from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_key
from backend.database import get_db
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from backend.services.email_service import send_order_notification


router = APIRouter()


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
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

        new_order = Order(
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
        response = OrderResponse.model_validate(new_order)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Schedule only after commit. JSON-mode data contains no SQLAlchemy objects.
    notification = response.model_dump(mode="json")
    for item in notification["items"]:
        item["product_name"] = product_names[item["product_id"]]
    background_tasks.add_task(send_order_notification, notification)
    return response


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
        order = db.get(Order, order_id)
        if order is None:
            raise HTTPException(404, "Order not found")

        order.status = status_update.status
        db.flush()
        response = OrderResponse.model_validate(order)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
