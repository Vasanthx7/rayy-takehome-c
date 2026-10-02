"""Payment webhook business rules. No HTTP here; the route calls into this.

The gateway delivers ``payment.succeeded`` at-least-once (see app/gateway.py),
so processing must verify the signature and be idempotent.
"""

import hmac
import json

from app.gateway import StubGateway
from app.repositories import orders as orders_repo
from app.services.orders import OrderNotFound


class BadSignature(Exception):
    pass


class MalformedWebhook(Exception):
    """A signed body we can't process: bad JSON, missing fields, wrong event,
    or a non-integer amount."""


class AmountMismatch(Exception):
    pass


EXPECTED_EVENT = "payment.succeeded"
REQUIRED_KEYS = ("event", "payment_id", "order_id", "amount_paise")

_gateway = StubGateway()


async def process_webhook(raw_body: bytes, signature: str | None) -> None:
    """Verify a signed ``payment.succeeded`` webhook and mark the order paid.

    Idempotent: a repeated delivery for an already-paid order is a no-op.
    """
    if signature is None or not hmac.compare_digest(_gateway.sign(raw_body), signature):
        raise BadSignature()

    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        raise MalformedWebhook("invalid JSON")
    if not isinstance(body, dict) or any(key not in body for key in REQUIRED_KEYS):
        raise MalformedWebhook("missing required fields")
    if body["event"] != EXPECTED_EVENT:
        raise MalformedWebhook(f"unexpected event {body['event']!r}")

    amount_paise = body["amount_paise"]
    # All money is integer paise; bool is an int subclass, so exclude it.
    if not isinstance(amount_paise, int) or isinstance(amount_paise, bool):
        raise MalformedWebhook("amount_paise must be an integer")

    order_id = body["order_id"]
    order = await orders_repo.get(order_id)
    if order is None:
        raise OrderNotFound(order_id)

    if amount_paise != order["total_paise"]:
        raise AmountMismatch(order_id)

    payment = {"payment_id": body["payment_id"], "amount_paise": amount_paise}
    # modified_count == 0 means the order was already paid (duplicate delivery):
    # a no-op, no second payment written.
    await orders_repo.mark_paid(order_id, payment)
