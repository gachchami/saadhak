"""Scoring the practitioner's probabilities, which is what earns it size.

The claim this project rests on is that a model should be trusted in proportion
to how well it knows what it knows, not how confident it sounds. That requires
the model to make falsifiable statements and requires us to score them.

Every review states a range forecast: the probability that the underlying closes
between lo and hi on the structure's expiry date. Those resolve on their own,
without needing a trade to close, so a useful score accumulates within a session
instead of after twenty trades. The score is a Brier score, the mean squared
error of stated probabilities: 0 is perfect, 0.25 is what you get by saying 50%
to everything, and being confidently wrong is punished hardest.
"""
from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime

from saadhak.broker.client import data
from saadhak.config import settings
from saadhak.witness import journal


@dataclass(frozen=True)
class Resolved:
    symbol: str
    expiry: date
    lo: float
    hi: float
    p: float
    close: float
    inside: bool

    @property
    def brier_contribution(self) -> float:
        return (self.p - (1.0 if self.inside else 0.0)) ** 2


@dataclass
class Calibration:
    brier: float | None
    n: int
    resolved: list[Resolved]
    mean_p: float | None = None
    hit_rate: float | None = None

    @property
    def verdict(self) -> str:
        if self.brier is None:
            return "no resolved forecasts yet; sizing uses the prior"
        if self.mean_p is not None and self.hit_rate is not None:
            gap = self.mean_p - self.hit_rate
            lean = ("overconfident" if gap > 0.05 else
                    "underconfident" if gap < -0.05 else "well calibrated")
            return (f"Brier {self.brier:.3f} over {self.n}; says {self.mean_p:.0%}, "
                    f"right {self.hit_rate:.0%} of the time -> {lean}")
        return f"Brier {self.brier:.3f} over {self.n}"


def daily_close(symbol: str, day: date) -> float | None:
    try:
        d = data(f"/v2/stocks/{symbol}/bars",
                 params={"timeframe": "1Day", "start": day.isoformat(),
                         "end": day.isoformat(), "feed": "iex", "limit": 1})
        bars = d.get("bars") or []
        return float(bars[0]["c"]) if bars else None
    except Exception:
        return None


def _all_records() -> list[dict]:
    out = []
    for path in sorted(glob.glob(str(journal.JOURNAL_DIR / "*.jsonl"))):
        with open(path) as f:
            for line in f:
                if line.strip():
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return out


def resolve_forecasts(*, write: bool = True) -> list[Resolved]:
    """Resolve every forecast whose expiry has passed and that is not yet scored."""
    records = _all_records()
    already = {
        (r["data"].get("symbol"), r["data"].get("expiry"))
        for r in records if r["type"] == "forecast_resolved"
    }
    today = datetime.now(UTC).date()
    out: list[Resolved] = []

    for r in records:
        if r["type"] != "thesis":
            continue
        d = r["data"]
        mf = d.get("micro_forecast")
        if not isinstance(mf, dict):
            continue
        struct = d.get("structure", "")
        parts = struct.split()
        if len(parts) < 2:
            continue
        symbol, expiry_s = parts[0], parts[1]
        if (symbol, expiry_s) in already:
            continue
        try:
            expiry = date.fromisoformat(expiry_s)
            lo, hi, p = float(mf["lo"]), float(mf["hi"]), float(mf["p"])
        except (ValueError, KeyError, TypeError):
            continue
        if expiry >= today:            # not yet resolvable
            continue
        close = daily_close(symbol, expiry)
        if close is None:
            continue
        res = Resolved(symbol, expiry, lo, hi, p, close, lo <= close <= hi)
        out.append(res)
        already.add((symbol, expiry_s))
        if write:
            journal.append("forecast_resolved", {
                "symbol": symbol, "expiry": expiry_s, "lo": lo, "hi": hi, "p": p,
                "close": close, "inside": res.inside,
                "brier_contribution": round(res.brier_contribution, 5)})
    return out


def current(*, resolve: bool = True) -> Calibration:
    """The Brier score over the most recent resolved forecasts."""
    if resolve:
        resolve_forecasts()
    s = settings()
    # Only the fixed-band task is scored. Earlier records let the model choose
    # its own range, which it widened until it could not miss: bands averaged
    # 3.3% of price against a 0.6% typical daily move, and it went 8 for 8. That
    # is a different, far easier question, and averaging the two produces a
    # number that describes neither.
    rows = [r["data"] for r in _all_records()
            if r["type"] == "forecast_resolved" and r["data"].get("task") == "fixed_band"]
    rows = rows[-s.calibration_window:]
    if not rows:
        return Calibration(None, 0, [])

    resolved = [
        Resolved(r["symbol"], date.fromisoformat(r["expiry"]), r["lo"], r["hi"],
                 r["p"], r["close"], r["inside"])
        for r in rows
    ]
    brier = sum(x.brier_contribution for x in resolved) / len(resolved)
    return Calibration(
        brier=round(brier, 4), n=len(resolved), resolved=resolved,
        mean_p=round(sum(x.p for x in resolved) / len(resolved), 4),
        hit_rate=round(sum(1 for x in resolved if x.inside) / len(resolved), 4),
    )
