from fastapi import APIRouter
from backend.schemas.order import OrderCreate

router = APIRouter()



@router.post("/orders")
def create_order(order: OrderCreate):
    return{
        "meassage": "Order received successfully",
        "order": order
    }