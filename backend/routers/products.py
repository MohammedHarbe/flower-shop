from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.product import Product
from backend.schemas.product import ProductCreate, ProductResponse


router = APIRouter()


@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    new_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        image_url=product.image_url
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product