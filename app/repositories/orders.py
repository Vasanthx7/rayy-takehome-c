"""All database access for the ``orders`` collection."""

from app.db import ORDERS, get_db


def _to_order_dict(doc: dict) -> dict:
    doc = dict(doc)
    doc["order_id"] = doc.pop("_id")
    return doc


async def get(order_id: str) -> dict | None:
    doc = await get_db()[ORDERS].find_one({"_id": order_id})
    return _to_order_dict(doc) if doc else None


async def list_recent(limit: int = 50) -> list[dict]:
    cursor = get_db()[ORDERS].find({}).sort("created_at", -1).limit(limit)
    return [_to_order_dict(doc) async for doc in cursor]


async def set_discount(order_id: str, discount: dict, new_total_paise: int) -> bool:
    """Atomically attach a discount to an order that has none and is unpaid.

    The filter is the concurrency gate: only one of several concurrent applies
    can match (``discount: None`` matches both a null field and a missing one).
    Returns whether a document was modified.
    """
    result = await get_db()[ORDERS].update_one(
        {"_id": order_id, "status": {"$ne": "paid"}, "discount": None},
        {"$set": {"discount": discount, "total_paise": new_total_paise}},
    )
    return result.modified_count == 1


async def mark_paid(order_id: str, payment: dict) -> bool:
    """Atomically mark an unpaid order paid and record the payment.

    The ``status != paid`` filter makes repeated webhook deliveries idempotent:
    only the first delivery modifies the order. Returns whether it did.
    """
    result = await get_db()[ORDERS].update_one(
        {"_id": order_id, "status": {"$ne": "paid"}},
        {"$set": {"status": "paid", "payment": payment}},
    )
    return result.modified_count == 1
