import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_key
from backend.database import get_db
from backend.delivery_region import DeliveryGovernorate
from backend.logging_utils import log_failure
from backend.models.delivery_zone import DeliveryZone
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.rate_limiter import enforce_rate_limit
from backend.settings import Settings
from backend.order_status import OrderStatus
from backend.payment_method import PaymentMethod
from backend.payment_status import PaymentStatus
from backend.schemas.delivery_zone import DeliveryZoneCreate, DeliveryZoneResponse, DeliveryZoneUpdate
from backend.schemas.order import (
    OrderConfirmationResponse,
    OrderCreate,
    OrderPaymentStatusUpdate,
    OrderResponse,
    OrderStatusUpdate,
)
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

PAYMENT_ALLOWED_TRANSITIONS = {
    PaymentStatus.awaiting_payment: {PaymentStatus.paid},
    PaymentStatus.unpaid: {PaymentStatus.paid},
    PaymentStatus.paid: set(),
}

ORDER_REQUEST_FIELDS = (
    "customer_name", "customer_phone", "customer_email", "receiver_name",
    "receiver_phone", "governorate", "delivery_address", "delivery_area",
    "delivery_date", "delivery_slot", "payment_method", "payment_status",
    "delivery_zone_id",
    "card_message", "sender_name_on_card", "customer_note",
)


def _delivery_zone_fee(db: Session, delivery_zone_id: int, governorate: DeliveryGovernorate) -> Decimal:
    zone = db.get(DeliveryZone, delivery_zone_id)
    if zone is None:
        raise HTTPException(404, "Delivery zone not found")
    if not zone.active:
        raise HTTPException(400, "Delivery zone is inactive")
    if zone.governorate != governorate:
        raise HTTPException(400, "Delivery zone does not match governorate")
    fee = Decimal(zone.fee)
    if fee <= 0:
        raise HTTPException(503, "Delivery is temporarily unavailable")
    return fee


def _replay_order(existing: Order, request: OrderCreate, http_response: Response | None) -> OrderResponse:
    same_fields = all(getattr(existing, field) == getattr(request, field) for field in ORDER_REQUEST_FIELDS)
    saved_items = sorted((item.product_id, item.quantity) for item in existing.items)
    requested_items = sorted((item.product_id, item.quantity) for item in request.items)
    if not same_fields or saved_items != requested_items:
        raise HTTPException(409, "Idempotency key already used for a different order")
    if http_response is not None:
        http_response.status_code = 200
    return OrderResponse.model_validate(existing)


@router.get("/delivery-zones", response_model=list[DeliveryZoneResponse])
def list_delivery_zones_public(db: Session = Depends(get_db)):
    return (
        db.query(DeliveryZone)
        .filter(DeliveryZone.active.is_(True), DeliveryZone.fee > Decimal("0.00"))
        .order_by(DeliveryZone.sort_order.asc(), DeliveryZone.id.asc())
        .all()
    )


@router.get("/delivery-zones/admin", response_model=list[DeliveryZoneResponse])
def list_delivery_zones_admin(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    return db.query(DeliveryZone).order_by(DeliveryZone.sort_order.asc(), DeliveryZone.id.asc()).all()


@router.post("/delivery-zones", response_model=DeliveryZoneResponse, status_code=201)
def create_delivery_zone(
    zone: DeliveryZoneCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    record = DeliveryZone(
        governorate=zone.governorate,
        name_en=zone.name_en,
        name_ar=zone.name_ar,
        fee=zone.fee,
        active=zone.active,
        sort_order=zone.sort_order,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/delivery-zones/{zone_id}", response_model=DeliveryZoneResponse)
def update_delivery_zone(
    zone_id: int,
    zone: DeliveryZoneUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    record = db.get(DeliveryZone, zone_id)
    if record is None:
        raise HTTPException(404, "Delivery zone not found")
    for field, value in zone.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.post("/orders", response_model=OrderConfirmationResponse, status_code=201)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    http_response: Response = None,
    request: Request = None,
):
    settings = Settings()
    enforce_rate_limit(request, name="orders", limit=settings.order_rate_limit_per_minute, window_seconds=60)
    key = str(order.idempotency_key)
    existing = db.query(Order).filter(Order.idempotency_key == key).one_or_none()
    if existing is not None:
        return _replay_order(existing, order, http_response)

    try:
        validated_items = []
        subtotal = Decimal("0.00")
        product_names = {}

        for item in order.items:
            product = db.get(Product, item.product_id)
            if product is None:
                raise HTTPException(404, f"Product {item.product_id} not found")
            if not product.active:
                raise HTTPException(400, f"Product {item.product_id} is inactive")

            unit_price = Decimal(product.price)
            item_subtotal = unit_price * item.quantity
            subtotal += item_subtotal
            product_names[product.id] = product.name
            validated_items.append((product, item.quantity, unit_price, item_subtotal))

        delivery_fee = _delivery_zone_fee(db, order.delivery_zone_id, order.governorate)
        total_price = subtotal + delivery_fee
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
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            delivery_zone_id=order.delivery_zone_id,
            card_message=order.card_message,
            sender_name_on_card=order.sender_name_on_card,
            customer_note=order.customer_note,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total_price=total_price,
        )
        db.add(new_order)
        db.flush()

        for product, quantity, unit_price, item_subtotal in validated_items:
            new_order.items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=item_subtotal,
                )
            )

        db.flush()
        order_response = OrderResponse.model_validate(new_order)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = db.query(Order).filter(Order.idempotency_key == key).one_or_none()
        if existing is not None:
            return _replay_order(existing, order, http_response)
        log_failure(logger, "Order insert failed without a matching idempotency key", error)
        raise HTTPException(500, "Could not save the order") from None
    except HTTPException:
        db.rollback()
        existing = db.query(Order).filter(Order.idempotency_key == key).one_or_none()
        if existing is not None:
            return _replay_order(existing, order, http_response)
        raise
    except Exception:
        db.rollback()
        raise

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


@router.patch("/orders/{order_id}/payment-status", response_model=OrderResponse)
def update_order_payment_status(
    order_id: int,
    payment_update: OrderPaymentStatusUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "Order not found")

    allowed_targets = PAYMENT_ALLOWED_TRANSITIONS.get(order.payment_status, set())
    if payment_update.status not in allowed_targets:
        raise HTTPException(409, f"Cannot change payment status from {order.payment_status.value} to {payment_update.status.value}")
    if (
        order.payment_method == PaymentMethod.vodafone_cash
        and payment_update.status == PaymentStatus.paid
        and order.status not in {
            OrderStatus.confirmed, OrderStatus.preparing,
            OrderStatus.out_for_delivery, OrderStatus.delivered,
        }
    ):
        raise HTTPException(409, "Confirm availability before marking Vodafone Cash payment as paid")

    order.payment_status = payment_update.status
    db.commit()
    db.refresh(order)
    return order


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    try:
        target = status_update.status
        allowed_sources = [source for source, destinations in ALLOWED_TRANSITIONS.items() if target in destinations]
        changed = db.execute(
            update(Order)
            .where(Order.id == order_id, Order.status.in_(allowed_sources))
            .values(status=target)
        )
        if changed.rowcount != 1:
            current_order = db.get(Order, order_id)
            if current_order is None:
                raise HTTPException(404, "Order not found")
            raise HTTPException(409, f"Cannot change order status from {current_order.status.value} to {target.value}")

        order = db.get(Order, order_id)
        db.flush()
        db.refresh(order)
        response = OrderResponse.model_validate(order)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
