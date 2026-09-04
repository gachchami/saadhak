"""Count correlated positions as one position, because that is what they are.

Gate 5 caps structures per underlying and treats SPY and QQQ as different names.
Their daily returns correlate at 0.91. Today the desk held a condor in each,
believed it was diversified across two underlyings, and was stopped out of both
within seventy seconds of the same rally. That is one position held twice.

Correlation is measured from daily closes rather than assumed from a table, so a
pair that decouples stops being penalised and a pair that tightens starts being
penalised without anyone editing a list.

This does not hedge direction. An iron condor is roughly delta-neutral when it is
written and becomes directional as the underlying moves toward a short strike,
and that is inherent to selling premium: the position is short gamma, and
neutralising it continuously would cost the premium that is the entire point.
What can be fixed cheaply is pretending that two views on the same index are two
positions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from saadhak.broker.client import data

CORRELATED_THRESHOLD = 0.80
_CACHE: dict[tuple[str, str], float] = {}


@dataclass(frozen=True)
class Cluster:
    blocked: bool
    reason: str
    correlated_with: list[str]


def _closes(symbol: str, sessions: int = 60) -> list[float]:
    end = datetime.now(UTC).date() - timedelta(days=1)
    start = end - timedelta(days=int(sessions * 1.8))
    try:
        d = data(f"/v2/stocks/{symbol}/bars",
                 params={"timeframe": "1Day", "feed": "iex", "limit": 300,
                         "start": start.isoformat(), "end": end.isoformat()})
        return [float(b["c"]) for b in (d.get("bars") or [])]
    except Exception:
        return []


def correlation(a: str, b: str) -> float | None:
    """Correlation of daily log returns. Cached for the life of the process."""
    if a == b:
        return 1.0
    key = tuple(sorted((a, b)))
    if key in _CACHE:
        return _CACHE[key]

    ca, cb = _closes(a), _closes(b)
    n = min(len(ca), len(cb))
    if n < 20:
        return None
    ra = [math.log(ca[-n:][i] / ca[-n:][i - 1]) for i in range(1, n)]
    rb = [math.log(cb[-n:][i] / cb[-n:][i - 1]) for i in range(1, n)]
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if va == 0 or vb == 0:
        return None
    r = cov / (va * vb)
    _CACHE[key] = r
    return r


def check(symbol: str, held: list[str], *,
          threshold: float = CORRELATED_THRESHOLD) -> Cluster:
    """Would opening `symbol` duplicate something already held?"""
    hits = []
    for h in set(held):
        r = correlation(symbol, h)
        if r is not None and r >= threshold:
            hits.append(f"{h} ({r:.2f})")
    if hits:
        return Cluster(True, f"already holding {', '.join(hits)}; at that "
                       f"correlation this is the same position, not a second one",
                       hits)
    return Cluster(False, "no correlated position open", [])
