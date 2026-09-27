from fastapi import FastAPI
from backend.routers.orders import router as orders_router

from backend.database import Base, engine
from backend.models.product import Product

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(orders_router)