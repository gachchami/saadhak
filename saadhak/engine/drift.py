"""Place the call strike further out than the put, because the index drifts up.

An iron condor sold at a symmetric delta treats a rise and a fall as equally
likely. Over 617 sessions SPY rose on 56% of days with a drift of about +19%
annualised, and at the distances our short strikes actually sit, a rise is the
more common event: moves beyond +0.75% happen 18.6% of the time against 13.5%
beyond -0.75%. The call side is breached roughly 1.4 times as often as the put
side for the same distance.

That asymmetry inverts further out. Beyond 1.5% the down-move is more likely,
because indices fall faster than they rise. But our exits cap each loss at one
credit rather than letting it run to the width, so what costs us money is how
*often* a strike is breached, not how far past it the market goes. At the
distances we trade, frequency favours the put side.

So the delta target is scaled per side rather than being one number: the call
strike is pushed further out in proportion to how much more often that side is
breached. This is not a directional bet. It is declining to sell both sides of a
distribution that is not symmetric as though it were.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from saadhak.broker.client import data

_CACHE: dict[str, "Asymmetry"] = {}


@dataclass(frozen=True)
class Asymmetry:
    symbol: str
    sessions: int
    up_share: float
    drift_annual: float
    breach_up: float
    breach_down: float

    @property
    def ratio(self) -> float:
        """How much more often the call side is breached than the put side."""
        return self.breach_up / self.breach_down if self.breach_down > 0 else 1.0

    def call_delta(self, base: float) -> float:
        """A call target scaled so both sides are breached about as often."""
        return max(0.02, base / max(self.ratio, 1e-6)) if self.ratio > 1 else base

    def put_delta(self, base: float) -> float:
        return base if self.ratio > 1 else max(0.02, base * self.ratio)

    @property
    def note(self) -> str:
        return (f"{self.symbol}: up {self.up_share:.0%} of {self.sessions} sessions, "
                f"drift {self.drift_annual:+.0%}/yr, call side breached "
                f"{self.ratio:.2f}x as often")


def measure(symbol: str, *, threshold: float = 0.0075,
            sessions: int = 600) -> Asymmetry | None:
    if symbol in _CACHE:
        return _CACHE[symbol]
    end = datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=int(sessions * 1.6))
    try:
        d = data(f"/v2/stocks/{symbol}/bars",
                 params={"timeframe": "1Day", "feed": "iex", "limit": 1000,
                         "start": start.isoformat(), "end": end.isoformat()})
        closes = [float(b["c"]) for b in (d.get("bars") or [])]
    except Exception:
        return None
    if len(closes) < 120:
        return None

    r = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    n = len(r)
    up = sum(1 for x in r if x > threshold) / n
    down = sum(1 for x in r if x < -threshold) / n
    if down <= 0:
        return None
    a = Asymmetry(symbol, n, sum(1 for x in r if x > 0) / n,
                  (1 + sum(r) / n) ** 252 - 1, up, down)
    _CACHE[symbol] = a
    return a
