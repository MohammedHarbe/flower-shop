from fastapi import FastAPI
from backend.routers.orders import router as orders_router

app = FastAPI()

app.include_router(orders_router)