from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    stock: int
    image_url: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: float
    stock: int
    active: bool
    image_url: str | None

    model_config = {
        "from_attributes": True
    }