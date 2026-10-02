# AI prompt history (readable version)

This is a clean, human-readable record of the AI session used for this take-home.
Each step shows **what I asked** and a short summary of **what the AI did**. The
full raw terminal log is in [`raw-transcript.txt`](./raw-transcript.txt).

Tool: Claude Code (Opus 4.8).

---

## 1. Set up project guidance

**I asked:** `/init` — look at the repo and write a CLAUDE.md for future sessions.

**The AI did:** Read the codebase and wrote `CLAUDE.md` summarising the commands,
the api → services → repositories layering, the "money is integer paise" rule,
how discount codes are config (not DB data), and the webhook contract.

---

## 2. Understand the codebase

**I asked:** Inspect the repo and explain the architecture, the order schema, the
payment-gateway stub and its failure modes, the test setup, which abstractions to
reuse, and the risks around duplicate webhooks, concurrent discounts, money
precision, and settlement. Separate facts from assumptions.

**The AI did:** Produced a full walkthrough of the request flow and data model,
flagged the key risks (at-least-once webhook delivery, read-modify-write races,
fractional-paise rounding, storing the wrong thing for settlement), and listed
open questions.

---

## 3. Spec out the behaviour (no code yet)

**I asked:** For each requirement, give the expected behaviour, data, validation,
failure cases, HTTP response, and a test scenario. Pay attention to expired/
unknown codes, the discount cap, funding split, rounding, a second discount,
duplicate webhooks, amount mismatches, paid orders, and concurrency. Mark what's
specified vs. what needs a decision. Don't implement yet.

**The AI did:** Wrote a requirement-by-requirement spec and clearly separated the
rules fixed by the brief from the ones left to my judgement (rounding, second
discount, HTTP status codes, concurrency approach).

---

## 4. Build the backend

**I asked:** Implement it using these decisions — 404 for unknown order/code,
400 for expired, 409 for already-paid / second discount, 401 for a bad webhook
signature, 400 for amount mismatch; round half-up; cap the discount; store the
actual partner/RAYY amounts and the split used; reject a second discount; make
concurrent requests safe with an atomic update; make duplicate webhooks
idempotent. Keep it simple and follow the existing structure.

**The AI did:** Added the money maths (`app/services/pricing.py`), the discount
and payment rules (`services/orders.py`, `services/payments.py`), atomic DB
writes (`repositories/orders.py`), and the two new routes. Wrote tests and got
the full suite green. Documented the decisions in `NOTES.md`.

---

## 5. Validate before moving on

**I asked:** Before the client, thoroughly validate the backend — run the tests,
exercise every case (including concurrent duplicate webhooks), confirm failed
requests don't partially change the order, check money is integer-only, and look
for races or unnecessary changes. Don't change anything yet.

**The AI did:** Ran the suite plus extra checks, confirmed no partial writes and
no races, and reported a few low-severity robustness gaps (a signed-but-malformed
webhook body, a missing integer check, the unchecked event type) and some missing
tests — without changing the code.

---

## 6. Harden + fill test gaps

**I asked:** Add the missing tests first and fix the low-severity gaps.

**The AI did:** Made the webhook reject malformed/missing/wrong-event/non-integer
bodies with 400, and added tests for concurrent duplicate webhooks, partial-write
safety, and a few edge cases.

---

## 7. Build the React client

**I asked:** Read the README and the client code first, then build the React
client — order summary (subtotal, discount, total via `formatPaise`) and the pay
flow (Pay → disabled while processing → Paid; show an error and allow retry on
failure). Add tests. Tell me what the README requires and which files you'll
change, then run the tests and verify. Don't change the backend.

**The AI did:** Implemented `formatPaise` and `OrderSummary` with tests, and gave
the UI a distinctive "studio enrollment slip" design (the orders are kids' art
classes). All client tests and type checks passed.

---

## 8. Small additions

**I asked:** Add two small tests — a negative-amount case for `formatPaise` and a
second real discount code (FIRST5) through apply-discount.

**The AI did:** Added both; all suites stayed green.

---

## 9. Loading state on the button

**I asked:** Add a loader to the Pay button once clicked and handle the button
states. Review against the README and run both test suites.

**The AI did:** Added a spinner shown while paying (the button still reads "Pay",
as the README requires), verified every button state against the brief, and ran
both suites green.

---

## 10. Final review

**I asked:** Do a final review of the whole assessment and run both test suites.

**The AI did:** Ran backend (36) and frontend (11) tests — all green — reviewed
everything against the README, caught and reverted one unintended change to the
demo file, and listed what's left for me to add (this prompt history, and two
personal notes).
