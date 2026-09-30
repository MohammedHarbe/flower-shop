from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, TypeAdapter, ValidationError, field_validator


ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
ShortTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PositivePrice = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
NonnegativeStock = Annotated[int, Field(ge=0)]
_IMAGE_URL_ADAPTER = TypeAdapter(HttpUrl)


def validate_image_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        url = _IMAGE_URL_ADAPTER.validate_python(value)
    except ValidationError as error:
        raise ValueError("image_url must be an absolute HTTP(S) URL") from error
    if url.username or url.password:
        raise ValueError("image_url cannot contain credentials")
    return str(url)


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

    @field_validator("image_url")
    @classmethod
    def image_url_must_be_http(cls, value: str | None) -> str | None:
        return validate_image_url(value)


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

    @field_validator("image_url")
    @classmethod
    def image_url_must_be_http(cls, value: str | None) -> str | None:
        return validate_image_url(value)

    @field_validator("name", "price", "stock", "active", "featured", "best_seller")
    @classmethod
    def required_columns_cannot_be_cleared(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value
