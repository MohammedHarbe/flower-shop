from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.delivery_region import DeliveryGovernorate
from backend.models.delivery_zone import DeliveryZone
from backend.order_status import OrderStatus
from backend.payment_method import PaymentMethod
from backend.payment_status import PaymentStatus
from backend.time_utils import CairoDateTime, cairo_now


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Nullable for orders created before idempotency keys were required.
    idempotency_key: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True, index=True)

    customer_name: Mapped[str] = mapped_column(String(150))
    customer_phone: Mapped[str] = mapped_column(String(30))
    customer_email: Mapped[str | None] = mapped_column(String(150), nullable=True)

    receiver_name: Mapped[str] = mapped_column(String(150))
    receiver_phone: Mapped[str] = mapped_column(String(30))

    delivery_address: Mapped[str] = mapped_column(String(500))
    # Nullable only to preserve orders created before governorate was recorded.
    governorate: Mapped[DeliveryGovernorate | None] = mapped_column(
        SAEnum(
            DeliveryGovernorate,
            native_enum=False,
            values_callable=lambda enum: [value.value for value in enum],
            validate_strings=True,
            length=20,
        ),
        nullable=True,
    )
    delivery_area: Mapped[str] = mapped_column(String(100))
    delivery_date: Mapped[date] = mapped_column(Date)
    # Historical orders have free-text values; new requests use DeliverySlot.
    delivery_slot: Mapped[str] = mapped_column(String(100))

    card_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sender_name_on_card: Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(
            PaymentMethod,
            native_enum=False,
            values_callable=lambda enum: [method.value for method in enum],
            validate_strings=True,
            length=30,
        ),
        default=PaymentMethod.cash_on_delivery,
        nullable=False,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            native_enum=False,
            values_callable=lambda enum: [status.value for status in enum],
            validate_strings=True,
            length=30,
        ),
        default=PaymentStatus.unpaid,
        nullable=False,
    )
    delivery_zone_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_zones.id"), nullable=True)
    delivery_zone: Mapped[DeliveryZone | None] = relationship(back_populates="orders")
    delivery_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            native_enum=False,
            values_callable=lambda enum: [status.value for status in enum],
            validate_strings=True,
            length=30,
        ),
        default=OrderStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(CairoDateTime(), default=cairo_now, nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(CairoDateTime(), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
