from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import Order
from app.services import orders as orders_service

router = APIRouter(prefix="/orders", tags=["orders"])


class DiscountRequest(BaseModel):
    code: str


@router.get("", response_model=list[Order])
async def list_orders(limit: int = 50) -> list[Order]:
    return await orders_service.list_orders(limit)


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: str) -> Order:
    try:
        return await orders_service.get_order(order_id)
    except orders_service.OrderNotFound:
        raise HTTPException(status_code=404, detail="order not found")


@router.post("/{order_id}/apply-discount", response_model=Order)
async def apply_discount(order_id: str, body: DiscountRequest) -> Order:
    try:
        return await orders_service.apply_discount(order_id, body.code)
    except orders_service.OrderNotFound:
        raise HTTPException(status_code=404, detail="order not found")
    except orders_service.CodeNotFound:
        raise HTTPException(status_code=404, detail="discount code not found")
    except orders_service.CodeExpired:
        raise HTTPException(status_code=400, detail="discount code expired")
    except orders_service.OrderAlreadyPaid:
        raise HTTPException(status_code=409, detail="order already paid")
    except orders_service.DiscountAlreadyApplied:
        raise HTTPException(status_code=409, detail="discount already applied")
