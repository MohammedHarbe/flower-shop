from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
ShortTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PositivePrice = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
NonnegativeStock = Annotated[int, Field(ge=0)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProductName
    name_ar: ProductName | None = None
    description: str | None = Field(default=None, max_length=500)
    description_ar: str | None = Field(default=None, max_length=500)
    price: PositivePrice
    stock: NonnegativeStock
    image_url: str | None = Field(default=None, max_length=500)
    category: ShortTag | None = None
    occasion: ShortTag | None = None
    featured: bool = False
    best_seller: bool = False


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_ar: str | None
    description: str | None
    description_ar: str | None
    price: Decimal
    stock: int
    active: bool
    image_url: str | None
    category: str | None
    occasion: str | None
    featured: bool
    best_seller: bool


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProductName | None = None
    name_ar: ProductName | None = None
    description: str | None = Field(default=None, max_length=500)
    description_ar: str | None = Field(default=None, max_length=500)
    price: PositivePrice | None = None
    stock: NonnegativeStock | None = None
    active: bool | None = None
    image_url: str | None = Field(default=None, max_length=500)
    category: ShortTag | None = None
    occasion: ShortTag | None = None
    featured: bool | None = None
    best_seller: bool | None = None

    @field_validator("name", "price", "stock", "active", "featured", "best_seller")
    @classmethod
    def required_columns_cannot_be_cleared(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value
