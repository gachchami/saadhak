"""Stop re-entering a trade the market keeps taking off us.

Today the desk sold three condors into the same rally and was stopped out of all
three. Every one of them passed the seventeen gates, and every stop fired
correctly, capping each loss near one credit rather than the full width. Nothing
malfunctioned. The flaw was upstream of all of it: nothing noticed that the
previous answer had just been wrong for the same reason.

Two independent checks, because they fail differently.

Consecutive stops are the market's own verdict on the strategy right now. A
strategy that sells range-bound premium is simply wrong while a trend is running,
and the fastest evidence of that is being stopped out twice in a row on the same
underlying. This is the same idea as the circuit breaker on the model provider:
after repeated refusals, stop asking for a while.

Realised drawdown is the account's verdict. The 3% daily halt is a long way from
where sensible people stop compounding a losing hypothesis, so a softer brake
sits in front of it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from saadhak.witness import journal


@dataclass(frozen=True)
class RegimeCheck:
    blocked: bool
    reason: str
    stops_today: int = 0
    stops_on_symbol: int = 0
    realised_today: float = 0.0


def _exits_today() -> list[dict]:
    today = datetime.now(UTC).date().isoformat()
    return [r["data"] for r in journal.read(today) if r["type"] == "exit"]


def check(symbol: str, *, max_consecutive_stops: int = 2,
          max_stops_per_day: int = 4, soft_loss_pct: float = 0.015,
          equity: float = 100_000.0) -> RegimeCheck:
    """Should we open anything at all on this underlying right now?"""
    exits = _exits_today()
    stops = [e for e in exits if e.get("rule") == "sl_2x"]
    realised = sum(float(e.get("pl") or 0) for e in exits)

    on_symbol = [e for e in stops if str(e.get("structure", "")).startswith(symbol)]

    # Consecutive stops on this underlying, counting back from the most recent exit.
    run = 0
    for e in reversed(exits):
        if not str(e.get("structure", "")).startswith(symbol):
            continue
        if e.get("rule") == "sl_2x":
            run += 1
        else:
            break

    if run >= max_consecutive_stops:
        return RegimeCheck(True, f"{run} consecutive stops on {symbol} today; the "
                           f"market is not paying for this structure right now",
                           len(stops), len(on_symbol), realised)

    if len(stops) >= max_stops_per_day:
        return RegimeCheck(True, f"{len(stops)} stop-outs across the desk today; "
                           f"the regime does not suit short premium",
                           len(stops), len(on_symbol), realised)

    if realised <= -abs(soft_loss_pct) * equity:
        return RegimeCheck(True, f"realised ${realised:,.0f} today, past the "
                           f"{soft_loss_pct:.1%} soft brake before the "
                           f"{3:.0f}% hard halt", len(stops), len(on_symbol), realised)

    return RegimeCheck(False, f"{len(stops)} stops today, ${realised:,.0f} realised",
                       len(stops), len(on_symbol), realised)
