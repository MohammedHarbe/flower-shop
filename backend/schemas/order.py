from pydantic import BaseModel
from datetime import date


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str | None = None

    receiver_name: str
    receiver_phone: str

    delivery_address: str
    delivery_area: str
    delivery_date: date
    delivery_slot: str

    card_message: str | None = None
    sender_name_on_card: str | None = None
    customer_note: str | None = None

    items: list[OrderItem]