from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.admin_auth import require_admin_key
from backend.database import get_db
from backend.models.product import Product
from backend.schemas.product import ProductCreate, ProductResponse, ProductUpdate


router = APIRouter()


@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    new_product = Product(**product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.get("/admin/products", response_model=list[ProductResponse])
def list_products_admin(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    return db.query(Product).order_by(Product.id.asc()).all()


@router.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.active.is_(True)).all()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.active.is_(True),
    ).first()
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin_key),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")

    for field, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product
