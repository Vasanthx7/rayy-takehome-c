"""Order business rules. No HTTP here; routes call into this module."""

from datetime import datetime, timezone

from app.models import Order
from app.repositories import discount_codes as codes_repo
from app.repositories import orders as orders_repo
from app.services import pricing


class OrderNotFound(Exception):
    pass


class CodeNotFound(Exception):
    pass


class CodeExpired(Exception):
    pass


class OrderAlreadyPaid(Exception):
    pass


class DiscountAlreadyApplied(Exception):
    pass


async def get_order(order_id: str) -> Order:
    doc = await orders_repo.get(order_id)
    if doc is None:
        raise OrderNotFound(order_id)
    return Order(**doc)


async def list_orders(limit: int = 50) -> list[Order]:
    return [Order(**doc) for doc in await orders_repo.list_recent(limit)]


async def apply_discount(order_id: str, code: str) -> Order:
    """Apply a partner discount code to an order and record what was applied.

    Rejects unknown/expired codes, already-paid orders, and a second discount.
    The persisted discount snapshots the funding split (amounts + bps) so a
    later change to the code's split cannot corrupt settlement.
    """
    order = await get_order(order_id)

    discount_code = codes_repo.get_by_code(code)
    if discount_code is None:
        raise CodeNotFound(code)
    if datetime.now(timezone.utc) >= discount_code.expires_at:
        raise CodeExpired(code)

    if order.status == "paid":
        raise OrderAlreadyPaid(order_id)
    if order.discount is not None:
        raise DiscountAlreadyApplied(order_id)

    amount = pricing.compute_discount(
        order.subtotal_paise, discount_code.percent_off_bps, discount_code.cap_paise
    )
    partner_amount, rayy_amount = pricing.split_funding(
        amount, discount_code.partner_share_bps
    )
    discount = {
        "code": discount_code.code,
        "amount_paise": amount,
        "partner_share_bps": discount_code.partner_share_bps,
        "rayy_share_bps": discount_code.rayy_share_bps,
        "partner_amount_paise": partner_amount,
        "rayy_amount_paise": rayy_amount,
    }
    new_total = order.subtotal_paise - amount

    # Atomic guard: loses to a concurrent apply (or a race that paid the order).
    if not await orders_repo.set_discount(order_id, discount, new_total):
        raise DiscountAlreadyApplied(order_id)

    return await get_order(order_id)
