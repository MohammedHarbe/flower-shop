from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DeliveryZoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    governorate: str
    name_en: str = Field(min_length=1, max_length=100)
    name_ar: str | None = Field(default=None, max_length=100)
    fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), max_digits=10, decimal_places=2)
    active: bool = True
    sort_order: int = Field(default=0, ge=0)


class DeliveryZoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    governorate: str | None = None
    name_en: str | None = Field(default=None, min_length=1, max_length=100)
    name_ar: str | None = Field(default=None, max_length=100)
    fee: Decimal | None = Field(default=None, ge=Decimal("0.00"), max_digits=10, decimal_places=2)
    active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class DeliveryZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    governorate: str
    name_en: str
    name_ar: str | None
    fee: Decimal
    active: bool
    sort_order: int
