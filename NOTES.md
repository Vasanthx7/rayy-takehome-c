# Engineering notes

Where the brief left decisions to me, what I chose and why, the trade-offs behind
those choices, and what I'd still improve. Meant to be read in a couple of
minutes.

## Overview

A FastAPI + MongoDB service with two new endpoints — apply a partner discount code
to an order, and process a payment webhook — plus a small screen showing the order
and a Pay button. All money is integer paise. I built the **React** client; the
Flutter starter is untouched.

## Running it

Full stack with Docker (Mongo replica set + API on `http://localhost:8000`, seeded
on boot):

```bash
docker compose up
```

Frontend:

```bash
cd client/web && npm ci && npm run dev
```

## Running the tests

Backend, against the real Mongo replica set (Docker):

```bash
docker compose up -d mongo                     # start Mongo, wait until it's healthy
docker compose run --rm api python -m pytest   # run the tests against it
```

Frontend:

```bash
cd client/web && npm ci && npm test
```

Current state: backend 36 passing, frontend 11 passing.

## Decisions the brief left open

- **Rounding a fraction of a paise — round half-up**, using integer maths only so
  there's no floating-point drift.
- **A second discount on an order that already has one — reject it (`409`).** One
  discount per order; I don't replace or stack.

Related choices, for consistency:

- The discount is the percentage of the subtotal, capped by the code's limit — a
  60%-off code capped at ₹40 takes ₹40 off a ₹149.99 order, not ₹89.99.
- Status codes: `404` unknown order/code, `400` expired code or payment-amount
  mismatch, `409` already paid or second discount, `401` bad/missing webhook
  signature.

## Settlement

Partners are paid monthly for their share, and a split can change next month, so I
can't recompute from the code later.

- **Stored per order:** the discount amount, the split percentages used at the
  time, and the exact partner and RAYY amounts in paise.
- **The monthly query:** sums each partner's stored amount for that month. It
  never re-reads the current code, so a change next month can't alter a past
  month's numbers.

## Concurrency and duplicate webhooks

Both writes use a single atomic, conditional update:

- **Apply discount** only succeeds if the order has no discount yet — two
  simultaneous requests give one winner and one `409`.
- **Webhook** only succeeds if the order isn't already paid — a repeated delivery
  does nothing the second time, so there's no double charge or duplicate record.

Single-document updates are atomic in MongoDB, so these hold under real
concurrency. I verified the full suite against the Docker replica set, the
concurrency cases included — all pass.

## One thing the AI got wrong that I caught

The task was small and the AI mostly handled it cleanly. The correction worth
noting: its first client was a plain, templated screen with a Pay button that gave
no feedback while processing — I redirected it to a proper design and a real
loading state (while keeping the label "Pay" during processing, as the brief
requires).

## What I wouldn't ship as-is

- Only successful-payment webhooks are handled — no failures, refunds, or
  chargebacks.
- Settlement is stored for but not built — there's no settlement report yet.
- Duplicate protection keys off the order being paid, not a log of processed
  payments; a second, different payment for an already-paid order is ignored
  rather than flagged.
- Rejecting a mismatched payment amount is my call; a real integration might
  record and reconcile instead.

## Time spent — about 2h 45m

- **~40 min** — reading the repo, understanding the architecture, and clarifying
  requirements before writing anything.
- **~1 hour** — backend: the discount and webhook logic, and their tests.
- **~1h 5m** — the React client and its tests, then validating everything
  end-to-end, including against the real Mongo replica set.
