import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_key
from backend.database import get_db
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.order_status import OrderStatus
from backend.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from backend.services.email_service import send_order_notification


router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS = {
    OrderStatus.pending: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.out_for_delivery, OrderStatus.cancelled},
    OrderStatus.out_for_delivery: {OrderStatus.delivered},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    http_response: Response = None,
):
    key = str(order.idempotency_key)
    existing = db.query(Order).filter(Order.idempotency_key == key).one_or_none()
    if existing is not None:
        if http_response is not None:
            http_response.status_code = 200
        return OrderResponse.model_validate(existing)

    try:
        validated_items = []
        total_price = Decimal("0.00")
        product_names = {}

        for item in order.items:
            product = db.get(Product, item.product_id)
            if product is None:
                raise HTTPException(404, f"Product {item.product_id} not found")
            if not product.active:
                raise HTTPException(400, f"Product {item.product_id} is inactive")
            if product.stock < item.quantity:
                raise HTTPException(409, f"Not enough stock for {product.name}")

            unit_price = Decimal(product.price)
            subtotal = unit_price * item.quantity
            total_price += subtotal
            product_names[product.id] = product.name
            validated_items.append((product, item.quantity, unit_price, subtotal))

        # Consistent lock order reduces deadlocks when PostgreSQL orders overlap.
        validated_items.sort(key=lambda entry: entry[0].id)
        new_order = Order(
            idempotency_key=key,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            customer_email=order.customer_email,
            receiver_name=order.receiver_name,
            receiver_phone=order.receiver_phone,
            governorate=order.governorate,
            delivery_address=order.delivery_address,
            delivery_area=order.delivery_area,
            delivery_date=order.delivery_date,
            delivery_slot=order.delivery_slot,
            card_message=order.card_message,
            sender_name_on_card=order.sender_name_on_card,
            customer_note=order.customer_note,
            total_price=total_price,
        )
        db.add(new_order)
        db.flush()

        for product, quantity, unit_price, subtotal in validated_items:
            new_order.items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )
            # Conditional update also protects against concurrent orders.
            result = db.execute(
                update(Product)
                .where(
                    Product.id == product.id,
                    Product.active.is_(True),
                    Product.stock >= quantity,
                )
                .values(stock=Product.stock - quantity)
            )
            if result.rowcount != 1:
                raise HTTPException(409, f"Product {product.id} is unavailable or out of stock")

        db.flush()
        order_response = OrderResponse.model_validate(new_order)
        db.commit()
    except IntegrityError:
        db.rollback()
        # A concurrent request may have committed the same key after our SELECT.
        existing = db.query(Order).filter(Order.idempotency_key == key).one_or_none()
        if existing is not None:
            if http_response is not None:
                http_response.status_code = 200
            return OrderResponse.model_validate(existing)
        logger.exception("Order insert failed without a matching idempotency key")
        raise HTTPException(500, "Could not save the order") from None
    except Exception:
        db.rollback()
        raise

    # Schedule only after commit. JSON-mode data contains no SQLAlchemy objects.
    notification = order_response.model_dump(mode="json")
    for item in notification["items"]:
        item["product_name"] = product_names[item["product_id"]]
    background_tasks.add_task(send_order_notification, notification)
    return order_response


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    status: OrderStatus | None = None,
    delivery_date: date | None = None,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    query = db.query(Order)
    if status is not None:
        query = query.filter(Order.status == status)
    if delivery_date is not None:
        query = query.filter(Order.delivery_date == delivery_date)
    return query.order_by(Order.created_at.desc(), Order.id.desc()).all()


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    # TODO: Replace the temporary API key with real administrator accounts/auth.
    try:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().one_or_none()
        if order is None:
            raise HTTPException(404, "Order not found")

        current = order.status
        target = status_update.status
        if target not in ALLOWED_TRANSITIONS[current]:
            raise HTTPException(409, f"Cannot change order status from {current.value} to {target.value}")

        items = sorted(order.items, key=lambda item: item.product_id) if target == OrderStatus.cancelled else []
        changed = db.execute(
            update(Order)
            .where(Order.id == order_id, Order.status == current)
            .values(status=target)
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Order status changed; refresh and try again")
        for item in items:
            restored = db.execute(
                update(Product)
                .where(Product.id == item.product_id)
                .values(stock=Product.stock + item.quantity)
            )
            if restored.rowcount != 1:
                raise HTTPException(409, f"Product {item.product_id} is missing; cancellation was rolled back")

        db.flush()
        db.refresh(order)
        response = OrderResponse.model_validate(order)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
