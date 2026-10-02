# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAYY take-home exercise: a small FastAPI + MongoDB service for applying partner
discount codes to orders and processing payment-gateway webhooks, with a client
starter (React or Flutter). The brief, acceptance criteria, and deliverables live
in `README.md` — read it before implementing; it defines the exact contracts
(e.g. `formatPaise` outputs, button states) that tests are graded against.

## Commands

```bash
make test        # run pytest against in-memory Mongo (mongomock); no Docker
make test-mongo  # run pytest against the docker-compose replica set (real transactions)
make run         # uvicorn app.main:app --reload
make seed        # load seed/orders.json into Mongo
docker compose up        # full stack: Mongo replica set + API on :8000 (seeds on boot)

python -m pytest tests/test_orders.py                      # single file
python -m pytest tests/test_orders.py::test_get_seeded_order  # single test
# (prefix with MONGO_URL=mongomock://localhost if not using `make`)
```

Client web (`client/web/`): `npm ci && npm test` (vitest), `npm run typecheck`.
Client Flutter (`client/flutter/`): `flutter pub get && flutter test`.

## Architecture

Strict layering — each route is thin, business logic sits below it:

```
app/api/*.py          HTTP only: routing, status codes, HTTPException mapping
app/services/*.py     business rules; raises domain exceptions (e.g. OrderNotFound)
app/repositories/*.py all Mongo queries; owns _id <-> order_id translation
app/db.py             lazy Mongo client (mongomock vs motor chosen by MONGO_URL)
```

Keep pricing and money logic **out of route handlers** — the README grades on
this. Routes call services; services call repositories; only repositories touch
`get_db()`. Services raise domain exceptions that routes translate to HTTP.

### Money and discounts

- **All money is integer paise.** Never use float arithmetic on amounts. The
  README leaves the rounding rule for fractional paise unspecified — decide it
  and document in `NOTES.md`.
- Discount codes are **partner config, not transactional data**: loaded from
  `seed/discount_codes.json` via `app/repositories/discount_codes.py` (cached
  with `lru_cache`), not stored in Mongo. Percentages are in **basis points**
  (`percent_off_bps`, 1500 = 15%); `partner_share_bps + rayy_share_bps = 10000`
  is the funding split used for monthly partner settlement.

### Payment gateway (`app/gateway.py`)

`StubGateway` stands in for the real SDK (no network calls). The webhook contract
is in its docstring: body signed with **HMAC-SHA256** over the raw bytes, hex,
in the `X-Gateway-Signature` header, keyed by `GATEWAY_WEBHOOK_SECRET`. Delivery
is **at-least-once** — `deliveries()` always returns the event twice — so the
`/webhooks/payment` handler must verify the signature and be **idempotent**.

### Persistence notes

- Mongo `_id` is the `order_id`; repositories translate between them. The client
  is created lazily so tests can set env vars before connecting.
- `mongomock` (default, `make test`) does **not support transactions**. If you
  use transactions, say so in `NOTES.md` — they only run under `make test-mongo`
  / the compose replica set.

## Tests

`tests/conftest.py` sets `MONGO_URL` to mongomock, wipes collections, and re-seeds
before each test needing the `db`/`client` fixtures. `pytest.ini` runs in
`asyncio_mode = auto`, so `async def test_*` functions need no decorator. Tests
drive the API through an ASGI `AsyncClient` (no live server).

## Unimplemented (the deliverables)

These are stubs to be built — see `README.md` for exact contracts:
- `POST /orders/{order_id}/apply-discount` and `POST /webhooks/payment` (new routes/services).
- `formatPaise` in `client/web/src/formatPaise.ts` and `client/flutter/lib/format_paise.dart`.
- `OrderSummary` in both clients (currently placeholder render).
- `NOTES.md` and a `prompts/` folder are **required** deliverables.
