"""POST /webhooks/payment — signed, idempotent payment handling."""

import asyncio
import json

from app.db import ORDERS
from app.gateway import SIGNATURE_HEADER, StubGateway

# Sign with the app's configured secret so these pass under both `make test`
# (mongomock; secret comes from conftest) and `make test-mongo` (the compose env
# sets a different GATEWAY_WEBHOOK_SECRET).
GATEWAY = StubGateway()


def _sign(raw: bytes) -> dict:
    return {SIGNATURE_HEADER: GATEWAY.sign(raw), "Content-Type": "application/json"}


def _signed(order_id: str, amount_paise: int, payment_id: str = "pay_test_1"):
    """Build the (content, headers) for a payment.succeeded webhook."""
    body = {
        "event": "payment.succeeded",
        "payment_id": payment_id,
        "order_id": order_id,
        "amount_paise": amount_paise,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    return raw, _sign(raw)


async def test_happy_path_marks_paid_and_records_payment(client):
    # ord_c_3003 has subtotal/total 45900 and no discount.
    raw, headers = _signed("ord_c_3003", 45900, payment_id="pay_c_9001")
    response = await client.post("/webhooks/payment", content=raw, headers=headers)
    assert response.status_code == 200

    order = (await client.get("/orders/ord_c_3003")).json()
    assert order["status"] == "paid"
    assert order["payment"] == {"payment_id": "pay_c_9001", "amount_paise": 45900}


async def test_missing_signature_is_401(client):
    raw, _ = _signed("ord_c_3003", 45900)
    response = await client.post("/webhooks/payment", content=raw)
    assert response.status_code == 401


async def test_bad_signature_is_401(client, db):
    raw, headers = _signed("ord_c_3003", 45900)
    headers[SIGNATURE_HEADER] = "deadbeef"
    response = await client.post("/webhooks/payment", content=raw, headers=headers)
    assert response.status_code == 401
    doc = await db[ORDERS].find_one({"_id": "ord_c_3003"})
    assert doc["status"] == "pending" and "payment" not in doc


async def test_unknown_order_is_404(client):
    raw, headers = _signed("ord_missing", 45900)
    response = await client.post("/webhooks/payment", content=raw, headers=headers)
    assert response.status_code == 404


async def test_amount_mismatch_is_400(client, db):
    raw, headers = _signed("ord_c_3003", 1)  # order total is 45900
    response = await client.post("/webhooks/payment", content=raw, headers=headers)
    assert response.status_code == 400
    doc = await db[ORDERS].find_one({"_id": "ord_c_3003"})
    assert doc["status"] == "pending" and "payment" not in doc


async def test_amount_checked_against_discounted_total(client):
    # After a discount, the payable amount is the reduced total, not the subtotal.
    await client.post("/orders/ord_c_3003/apply-discount", json={"code": "KIDS18"})
    discounted = (await client.get("/orders/ord_c_3003")).json()["total_paise"]
    assert discounted < 45900

    stale, headers = _signed("ord_c_3003", 45900)  # pre-discount amount
    assert (await client.post("/webhooks/payment", content=stale, headers=headers)).status_code == 400

    raw, headers = _signed("ord_c_3003", discounted)
    assert (await client.post("/webhooks/payment", content=raw, headers=headers)).status_code == 200


async def test_duplicate_delivery_is_idempotent(client, db):
    # The gateway delivers twice; the second must be a no-op.
    raw, headers = _signed("ord_c_3003", 45900, payment_id="pay_c_9001")
    first = await client.post("/webhooks/payment", content=raw, headers=headers)
    second = await client.post("/webhooks/payment", content=raw, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200

    order = await db[ORDERS].find_one({"_id": "ord_c_3003"})
    assert order["status"] == "paid"
    assert order["payment"] == {"payment_id": "pay_c_9001", "amount_paise": 45900}


async def test_concurrent_duplicate_deliveries_pay_once(client, db):
    # Five simultaneous deliveries of the same payment: paid once, one payment.
    raw, headers = _signed("ord_c_3003", 45900, payment_id="pay_c_9001")
    results = await asyncio.gather(
        *[client.post("/webhooks/payment", content=raw, headers=headers) for _ in range(5)]
    )
    assert all(r.status_code == 200 for r in results)
    doc = await db[ORDERS].find_one({"_id": "ord_c_3003"})
    assert doc["status"] == "paid"
    assert doc["payment"] == {"payment_id": "pay_c_9001", "amount_paise": 45900}


async def test_second_distinct_payment_is_ignored(client, db):
    # First payment wins; a later distinct payment_id for a paid order is a no-op.
    raw1, h1 = _signed("ord_c_3003", 45900, payment_id="pay_first")
    assert (await client.post("/webhooks/payment", content=raw1, headers=h1)).status_code == 200
    raw2, h2 = _signed("ord_c_3003", 45900, payment_id="pay_second")
    assert (await client.post("/webhooks/payment", content=raw2, headers=h2)).status_code == 200
    doc = await db[ORDERS].find_one({"_id": "ord_c_3003"})
    assert doc["payment"]["payment_id"] == "pay_first"


async def test_malformed_but_signed_body_is_400(client, db):
    raw = b"{not valid json"
    response = await client.post("/webhooks/payment", content=raw, headers=_sign(raw))
    assert response.status_code == 400
    assert (await db[ORDERS].find_one({"_id": "ord_c_3003"}))["status"] == "pending"


async def test_missing_fields_is_400(client):
    raw = json.dumps({"event": "payment.succeeded"}, separators=(",", ":")).encode()
    response = await client.post("/webhooks/payment", content=raw, headers=_sign(raw))
    assert response.status_code == 400


async def test_unexpected_event_is_400(client, db):
    body = {
        "event": "payment.refunded",
        "payment_id": "pay_x",
        "order_id": "ord_c_3003",
        "amount_paise": 45900,
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    response = await client.post("/webhooks/payment", content=raw, headers=_sign(raw))
    assert response.status_code == 400
    assert (await db[ORDERS].find_one({"_id": "ord_c_3003"}))["status"] == "pending"


async def test_non_integer_amount_is_400(client):
    body = {
        "event": "payment.succeeded",
        "payment_id": "pay_x",
        "order_id": "ord_c_3003",
        "amount_paise": 45900.0,  # float — money must be integer paise
    }
    raw = json.dumps(body, separators=(",", ":")).encode()
    response = await client.post("/webhooks/payment", content=raw, headers=_sign(raw))
    assert response.status_code == 400
