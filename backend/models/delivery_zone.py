from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.delivery_region import DeliveryGovernorate

if TYPE_CHECKING:
    from backend.models.order import Order


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    governorate: Mapped[DeliveryGovernorate] = mapped_column(
        SAEnum(
            DeliveryGovernorate,
            native_enum=False,
            values_callable=lambda enum: [value.value for value in enum],
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="delivery_zone")
