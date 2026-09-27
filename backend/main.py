from fastapi import FastAPI
from backend.routers.orders import router as orders_router

from backend.database import Base, engine
from backend.models.product import Product

from backend.routers.products import router as products_router
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(orders_router)
app.include_router(products_router)