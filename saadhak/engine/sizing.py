"""How many contracts. Max loss is capped by book, then scaled by calibration."""
from __future__ import annotations

from saadhak.config import settings
from saadhak.engine.structures import Structure


def calibration_multiplier(brier: float | None) -> float:
    """A model that knows what it knows earns full size.
    Brier 0.10 -> 1.00x, 0.25 (coin flip) -> 0.70x, >=0.475 -> 0.25x."""
    s = settings()
    b = s.prior_brier if brier is None else brier
    return max(0.25, min(1.0, 1.0 - 2.0 * (b - 0.10)))


def size_structure(structure: Structure, equity: float, *, brier: float | None = None,
                   open_risk: float = 0.0) -> tuple[int, dict]:
    """Return (qty, explanation). qty 0 means the trade cannot be sized."""
    s = settings()
    cap_pct = s.max_loss_pct_book_a if structure.book == "A" else s.max_loss_pct_book_b
    mult = calibration_multiplier(brier)
    budget = equity * cap_pct * mult

    per_unit = structure.max_loss_per_unit
    if per_unit <= 0:
        return 0, {"reason": "non-positive max loss per unit"}

    qty = int(budget // per_unit)

    # portfolio headroom
    headroom = equity * s.max_portfolio_risk_pct - open_risk
    if headroom <= 0:
        return 0, {"reason": "no portfolio risk headroom", "headroom": round(headroom, 2)}
    qty = min(qty, int(headroom // per_unit))

    return max(qty, 0), {
        "equity": equity, "cap_pct": cap_pct, "brier": brier,
        "multiplier": round(mult, 3), "budget": round(budget, 2),
        "max_loss_per_unit": per_unit, "open_risk": round(open_risk, 2),
        "headroom": round(headroom, 2), "qty": max(qty, 0),
    }
