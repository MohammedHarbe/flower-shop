from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator

from backend.delivery_region import DeliveryGovernorate
from backend.delivery_slot import DeliverySlot
from backend.order_status import OrderStatus
from backend.phone import normalize_egyptian_mobile
from backend.time_utils import cairo_today


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Area = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: UUID
    customer_name: Name
    customer_phone: str
    customer_email: EmailStr | None = Field(default=None, max_length=150)

    receiver_name: Name
    receiver_phone: str

    governorate: DeliveryGovernorate
    delivery_address: Address
    delivery_area: Area
    delivery_date: date
    delivery_slot: DeliverySlot

    card_message: str | None = Field(default=None, max_length=500)
    sender_name_on_card: str | None = Field(default=None, max_length=150)
    customer_note: str | None = Field(default=None, max_length=500)

    items: list[OrderItem] = Field(min_length=1)

    @field_validator("customer_phone", "receiver_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_egyptian_mobile(value)

    @field_validator("delivery_date")
    @classmethod
    def delivery_date_not_past(cls, value: date) -> date:
        if value < cairo_today():
            raise ValueError("Delivery date cannot be in the past")
        return value

    @model_validator(mode="after")
    def unique_products(self) -> "OrderCreate":
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product_id may appear only once in an order")
        return self


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idempotency_key: UUID | None
    customer_name: str
    customer_phone: str
    customer_email: str | None

    receiver_name: str
    receiver_phone: str

    governorate: DeliveryGovernorate | None
    delivery_address: str
    delivery_area: str
    delivery_date: date
    delivery_slot: str

    card_message: str | None
    sender_name_on_card: str | None
    customer_note: str | None

    status: OrderStatus
    total_price: Decimal
    created_at: datetime
    notified_at: datetime | None

    items: list[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus
