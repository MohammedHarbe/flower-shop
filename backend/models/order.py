from datetime import date, datetime

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Numeric
)
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    customer_name: Mapped[str] = mapped_column(String(150))
    customer_phone: Mapped[str] = mapped_column(String(30))
    customer_email: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    receiver_name: Mapped[str] = mapped_column(String(150))
    receiver_phone: Mapped[str] = mapped_column(String(30))

    delivery_address: Mapped[str] = mapped_column(String(500))
    delivery_area: Mapped[str] = mapped_column(String(100))
    delivery_date: Mapped[date] = mapped_column(Date)
    delivery_slot: Mapped[str] = mapped_column(String(100))

    card_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    sender_name_on_card: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    customer_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    total_price: Mapped[float] = mapped_column(Numeric(10, 2))

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id")
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id")
    )

    quantity: Mapped[int] = mapped_column(Integer)

    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))