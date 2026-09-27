from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.order import OrderCreate
from backend.models.order import Order, OrderItem
from backend.models.product import Product


router = APIRouter()


@router.post("/orders")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db)
):
    total_price = Decimal("0.00")

    validated_items = []

    for item in order.items:

        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.active == True
        ).first()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for {product.name}"
            )

        subtotal = product.price * item.quantity

        total_price += subtotal

        validated_items.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": product.price,
            "subtotal": subtotal
        })

    new_order = Order(
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_email=order.customer_email,

        receiver_name=order.receiver_name,
        receiver_phone=order.receiver_phone,

        delivery_address=order.delivery_address,
        delivery_area=order.delivery_area,
        delivery_date=order.delivery_date,
        delivery_slot=order.delivery_slot,

        card_message=order.card_message,
        sender_name_on_card=order.sender_name_on_card,
        customer_note=order.customer_note,

        total_price=total_price
    )

    db.add(new_order)

    db.flush()

    for item in validated_items:

        new_order_item = OrderItem(
            order_id=new_order.id,
            product_id=item["product"].id,
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            subtotal=item["subtotal"]
        )

        db.add(new_order_item)

        item["product"].stock -= item["quantity"]

    db.commit()

    db.refresh(new_order)

    return {
        "message": "Order created successfully",
        "order_id": new_order.id,
        "status": new_order.status,
        "total_price": new_order.total_price
    }


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()

    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "receiver_name": order.receiver_name,
        "receiver_phone": order.receiver_phone,
        "delivery_address": order.delivery_address,
        "delivery_area": order.delivery_area,
        "delivery_date": order.delivery_date,
        "delivery_slot": order.delivery_slot,
        "card_message": order.card_message,
        "customer_note": order.customer_note,
        "status": order.status,
        "total_price": order.total_price,
        "created_at": order.created_at,

        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal
            }
            for item in items
        ]
    }