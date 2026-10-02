"""Pure money maths — no DB, no async."""

from app.services import pricing


def test_percentage_rounds_half_up():
    # 1 * 5000 / 10000 = 0.5 -> 1 ; 1 * 4999 / 10000 = 0.4999 -> 0
    assert pricing.compute_discount(1, 5000, 99999) == 1
    assert pricing.compute_discount(1, 4999, 99999) == 0


def test_cap_binds():
    # SUPER60 (6000 bps) on 14999 is ~8999 paise, capped at 4000.
    assert pricing.compute_discount(14999, 6000, 4000) == 4000


def test_cap_does_not_bind():
    # KIDS18 (1800 bps) on 14999 -> 2700, well under the 80000 cap.
    assert pricing.compute_discount(14999, 1800, 80000) == 2700


def test_split_resums_to_discount():
    for discount in (4000, 2700, 1, 9999, 12345):
        for bps in (0, 1500, 5500, 7000, 8500, 10000):
            partner, rayy = pricing.split_funding(discount, bps)
            assert partner + rayy == discount
            assert partner >= 0 and rayy >= 0


def test_split_example():
    # discount 4000, partner 55% -> 2200 / 1800
    assert pricing.split_funding(4000, 5500) == (2200, 1800)
