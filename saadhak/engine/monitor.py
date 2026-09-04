"""Exit rules. Attached at entry, enforced here, never decided by a model."""
from __future__ import annotations

from dataclasses import dataclass

from saadhak.config import settings


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    rule: str
    detail: str


def attach_exit_rules(structure) -> None:
    """Record take-profit and stop levels on the structure at entry (gate 15)."""
    s = settings()
    credit = structure.net_credit
    structure.meta["entry_credit"] = credit
    structure.meta["tp_price"] = round(credit * (1 - s.take_profit_pct), 2)
    structure.meta["sl_price"] = round(credit * s.stop_loss_multiple, 2)
    structure.meta["time_stop_min_to_close"] = 15
    structure.meta["proximity_pct"] = s.proximity_pct


def check_exit(structure, current_cost: float, spot: float,
               minutes_to_close: float | None) -> ExitDecision:
    """current_cost is what it costs now to close the structure (positive = debit to close)."""
    s = settings()
    entry = structure.meta.get("entry_credit", structure.net_credit)
    tp = structure.meta.get("tp_price", round(entry * (1 - s.take_profit_pct), 2))
    sl = structure.meta.get("sl_price", round(entry * s.stop_loss_multiple, 2))

    if current_cost <= tp:
        return ExitDecision(True, "tp_50pct",
                            f"cost to close ${current_cost:.2f} <= target ${tp:.2f} "
                            f"({s.take_profit_pct:.0%} of ${entry:.2f} credit)")
    if current_cost >= sl:
        return ExitDecision(True, "sl_2x",
                            f"cost to close ${current_cost:.2f} >= stop ${sl:.2f} "
                            f"({s.stop_loss_multiple:g}x credit)")
    if minutes_to_close is not None and minutes_to_close <= 15 and structure.expiry.isoformat():
        return ExitDecision(True, "time_stop", f"{minutes_to_close:.0f}m to close on expiry day")
    if minutes_to_close is not None and minutes_to_close <= 30:
        for k in structure.short_strikes:
            if abs(k - spot) / spot <= s.proximity_pct:
                return ExitDecision(True, "proximity",
                                    f"short strike {k:g} within {s.proximity_pct:.1%} of spot {spot:.2f}")
    return ExitDecision(False, "hold", f"cost ${current_cost:.2f} between ${tp:.2f} and ${sl:.2f}")
