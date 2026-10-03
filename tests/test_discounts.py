"""POST /orders/{id}/apply-discount — fixtures mirror seed/fixtures.json."""

import asyncio

from app.db import ORDERS


async def test_apply_happy_path_caps_and_snapshots_split(client):
    # apply_1: SUPER60 on ord_c_3002 (subtotal 14999). 60% is capped at 4000.
    response = await client.post("/orders/ord_c_3002/apply-discount", json={"code": "SUPER60"})
    assert response.status_code == 200
    body = response.json()
    assert body["discount"]["code"] == "SUPER60"
    assert body["discount"]["amount_paise"] == 4000  # cap binds
    assert body["total_paise"] == 14999 - 4000
    # split snapshot: partner 55% of 4000 = 2200, RAYY 1800
    assert body["discount"]["partner_amount_paise"] == 2200
    assert body["discount"]["rayy_amount_paise"] == 1800
    assert body["discount"]["partner_share_bps"] == 5500
    assert body["discount"]["rayy_share_bps"] == 4500


async def test_apply_non_exact_split_persists(client):
    # KIDS18 on ord_c_3005 (38997): 1800bps -> 7019.46 -> 7019 (half-up).
    # 70% partner share -> 4913.3 -> 4913, RAYY takes the complement 2106.
    response = await client.post("/orders/ord_c_3005/apply-discount", json={"code": "KIDS18"})
    assert response.status_code == 200
    body = response.json()
    assert body["discount"]["amount_paise"] == 7019
    assert body["total_paise"] == 38997 - 7019
    assert body["discount"]["partner_amount_paise"] == 4913
    assert body["discount"]["rayy_amount_paise"] == 2106
    assert body["discount"]["partner_amount_paise"] + body["discount"]["rayy_amount_paise"] == 7019


async def test_apply_first5_records_amount_and_split(client):
    # FIRST5: 500bps (no cap bind), 85/15 split, on ord_c_3001 (subtotal 14999).
    # 14999 * 500 / 10000 = 749.95 -> 750; partner 85% -> 637.5 -> 638, RAYY 112.
    response = await client.post("/orders/ord_c_3001/apply-discount", json={"code": "FIRST5"})
    assert response.status_code == 200
    body = response.json()
    assert body["discount"]["code"] == "FIRST5"
    assert body["discount"]["amount_paise"] == 750
    assert body["total_paise"] == 14999 - 750
    assert body["discount"]["partner_amount_paise"] == 638
    assert body["discount"]["rayy_amount_paise"] == 112


async def test_apply_kids18_on_ord_c_3001(client):
    # apply_2 (fixtures.json): KIDS18 on ord_c_3001 (subtotal 14999).
    # 1800bps -> 2699.82 -> 2700 (half-up); 70/30 split -> partner 1890, RAYY 810.
    response = await client.post("/orders/ord_c_3001/apply-discount", json={"code": "KIDS18"})
    assert response.status_code == 200
    body = response.json()
    assert body["discount"]["code"] == "KIDS18"
    assert body["discount"]["amount_paise"] == 2700
    assert body["total_paise"] == 12299
    assert body["discount"]["partner_amount_paise"] == 1890
    assert body["discount"]["rayy_amount_paise"] == 810


async def test_unknown_code_is_404_and_no_partial_write(client, db):
    before = await db[ORDERS].find_one({"_id": "ord_c_3001"})
    response = await client.post("/orders/ord_c_3001/apply-discount", json={"code": "NOPE"})
    assert response.status_code == 404
    after = await db[ORDERS].find_one({"_id": "ord_c_3001"})
    assert after == before and "discount" not in after


async def test_unknown_order_is_404(client):
    response = await client.post("/orders/ord_missing/apply-discount", json={"code": "KIDS18"})
    assert response.status_code == 404


async def test_expired_code_is_400_and_no_partial_write(client, db):
    # apply_3: PAST30 (expires_in_days -1) on ord_c_3002.
    before = await db[ORDERS].find_one({"_id": "ord_c_3002"})
    response = await client.post("/orders/ord_c_3002/apply-discount", json={"code": "PAST30"})
    assert response.status_code == 400
    after = await db[ORDERS].find_one({"_id": "ord_c_3002"})
    assert after == before and "discount" not in after


async def test_missing_code_body_is_422(client):
    response = await client.post("/orders/ord_c_3001/apply-discount", json={})
    assert response.status_code == 422


async def test_second_discount_is_409(client):
    # apply_5: KIDS18 then FIRST5 on ord_c_3004, one after another.
    first = await client.post("/orders/ord_c_3004/apply-discount", json={"code": "KIDS18"})
    assert first.status_code == 200
    second = await client.post("/orders/ord_c_3004/apply-discount", json={"code": "FIRST5"})
    assert second.status_code == 409


async def test_already_paid_is_409(client, db):
    await db[ORDERS].update_one({"_id": "ord_c_3001"}, {"$set": {"status": "paid"}})
    response = await client.post("/orders/ord_c_3001/apply-discount", json={"code": "KIDS18"})
    assert response.status_code == 409


async def test_concurrent_apply_only_one_wins(client):
    # apply_4: KIDS18 and FIRST5 on ord_c_3005 at the same time.
    results = await asyncio.gather(
        client.post("/orders/ord_c_3005/apply-discount", json={"code": "KIDS18"}),
        client.post("/orders/ord_c_3005/apply-discount", json={"code": "FIRST5"}),
    )
    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 409]
    # exactly one discount is recorded
    final = await client.get("/orders/ord_c_3005")
    assert final.json()["discount"] is not None
