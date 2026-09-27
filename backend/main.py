from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.orders import router as orders_router
from backend.routers.products import router as products_router
from backend.settings import Settings


app = FastAPI(title="ToneFlowers API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)
app.include_router(orders_router)
app.include_router(products_router)
