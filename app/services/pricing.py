"""Pure money maths for discounts. Integer paise only, no I/O.

Rounding rule: **round half-up** on the fractional paise a percentage produces
(see NOTES.md). All inputs and outputs are integer paise / basis points.
"""


def _round_half_up(numerator: int, denominator: int) -> int:
    """Divide two non-negative ints, rounding halves up. Integer maths only."""
    return (numerator + denominator // 2) // denominator


def compute_discount(subtotal_paise: int, percent_off_bps: int, cap_paise: int) -> int:
    """Discount in paise: ``subtotal * bps / 10000`` (half-up), clamped to the cap.

    ``percent_off_bps`` is basis points (1500 = 15%); ``cap_paise`` is the most
    the code can take off one order.
    """
    discount = _round_half_up(subtotal_paise * percent_off_bps, 10000)
    return min(discount, cap_paise)


def split_funding(discount_paise: int, partner_share_bps: int) -> tuple[int, int]:
    """Split a discount into (partner_amount, rayy_amount).

    The partner share is rounded half-up and RAYY takes the complement, so the
    two always re-sum to ``discount_paise`` exactly (no lost or extra paise).
    """
    partner = _round_half_up(discount_paise * partner_share_bps, 10000)
    rayy = discount_paise - partner
    return partner, rayy
