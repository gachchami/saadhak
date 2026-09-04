"""Practice (sādhanā): earn a calibration score before risking size on one.

A desk that has never been scored is not "neutral", it is unmeasured, and sizing
it on a guessed prior is the thing this project claims not to do. So before the
practitioner is trusted with size, it forecasts days that have already happened
and is scored on them immediately.

The only thing that makes this honest is the lookahead discipline. For a target
day D the model is shown bars strictly up to D-1: the close it is being asked to
predict, and every bar after it, are never fetched into the prompt. The forecast
is then resolved against D's actual close, which the model never saw.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from saadhak.broker.client import data
from saadhak.practitioner.llm import ask_json
from saadhak.witness import journal

SYSTEM = """You estimate probabilities for a trading desk. The desk gives you a \
fixed price range and asks one question: how likely is the close to land inside \
it?

You do not choose the range. This is deliberate. A forecaster allowed to pick \
both the range and the probability can score well by naming a range so wide it \
cannot miss, which is accurate and useless. With the range fixed, the only thing \
your answer carries is judgement about this particular day.

You are scored with a Brier score, and it sets how much money the desk is allowed \
to risk. Probabilities near 0 or 1 are rewarded when right and punished hard when \
wrong. If the honest answer is close to even, say so.

Reply with a JSON object ONLY, exactly these keys:
{"p": <number 0-1>, "reasoning": "<one sentence>"}"""


@dataclass
class PracticeRound:
    symbol: str
    target: date
    lo: float
    hi: float
    p: float
    close: float
    inside: bool
    reasoning: str = ""

    @property
    def brier_contribution(self) -> float:
        return (self.p - (1.0 if self.inside else 0.0)) ** 2


def _bars(symbol: str, start: date, end: date) -> list[dict]:
    d = data(f"/v2/stocks/{symbol}/bars",
             params={"timeframe": "1Day", "start": start.isoformat(),
                     "end": end.isoformat(), "feed": "iex", "limit": 200})
    return d.get("bars") or []


def _history_block(bars: list[dict]) -> str:
    rows = [f"  {b['t'][:10]}  open {b['o']:.2f}  high {b['h']:.2f}  "
            f"low {b['l']:.2f}  close {b['c']:.2f}" for b in bars[-12:]]
    closes = [b["c"] for b in bars]
    moves = [abs(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    avg = sum(moves) / len(moves) if moves else 0.0
    return ("\n".join(rows) +
            f"\n  average absolute daily move over {len(moves)} sessions: {avg:.2%}")


def _all_records_safe() -> list[dict]:
    """Journal records, tolerant of a missing or partial file."""
    from saadhak.witness.calibration import _all_records
    try:
        return _all_records()
    except Exception:
        return []


def one_round(symbol: str, target: date, *, cycle_id: str = "",
              feedback: str = "", band: float = 0.9) -> PracticeRound | None:
    """Forecast `target`'s close using only bars strictly before it."""
    hist = _bars(symbol, target - timedelta(days=40), target - timedelta(days=1))
    if len(hist) < 8:
        return None
    # Belt and braces against lookahead: drop anything dated on or after target.
    hist = [b for b in hist if b["t"][:10] < target.isoformat()]
    if len(hist) < 8:
        return None

    last = hist[-1]
    ref = float(last["c"])
    # The engine sets the range, scaled to how much this name actually moves, so
    # the question is roughly a coin-flip for an uninformed forecaster and skill
    # is the only thing that can beat it.
    closes = [b["c"] for b in hist]
    moves = [abs(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    typical = (sum(moves) / len(moves)) if moves else 0.01
    half = ref * typical * band
    lo, hi = round(ref - half, 2), round(ref + half, 2)

    prompt = (f"Estimate the probability that {symbol} CLOSES between {lo:.2f} and "
              f"{hi:.2f} on {target:%A %d %B %Y}.\n\n"
              f"That band is {2 * half / ref:.2%} wide, against a typical daily move "
              f"of {typical:.2%} for this name, so it is close to an even question.\n\n"
              f"You know only what follows. The last session before the target "
              f"closed at {ref:.2f} on {last['t'][:10]}.\n\n"
              f"Recent daily bars:\n{_history_block(hist)}")
    if feedback:
        prompt = f"{feedback}\n\n---\n\n{prompt}"

    reply = ask_json(SYSTEM, prompt, cycle_id=cycle_id)
    if not reply.ok or not reply.parsed:
        return None
    try:
        p = float(reply.parsed["p"])
    except (KeyError, TypeError, ValueError):
        return None
    if not 0.0 <= p <= 1.0:
        return None

    actual = _bars(symbol, target, target)
    if not actual:
        return None
    close = float(actual[0]["c"])

    return PracticeRound(symbol, target, lo, hi, p, close, lo <= close <= hi,
                         str(reply.parsed.get("reasoning", ""))[:300])


def trading_days_back(symbol: str, n: int) -> list[date]:
    """The last n sessions that actually traded, ending yesterday."""
    today = datetime.now(UTC).date()
    bars = _bars(symbol, today - timedelta(days=n * 3 + 20), today - timedelta(days=1))
    return [date.fromisoformat(b["t"][:10]) for b in bars][-n:]


def run(symbols: list[str], sessions: int = 8, *, write: bool = True) -> list[PracticeRound]:
    """Forecast recent sessions and score them. Journalled as resolved forecasts."""
    out: list[PracticeRound] = []
    cycle = f"practice-{datetime.now(UTC):%Y%m%dT%H%M%S}"
    for symbol in symbols:
        for target in trading_days_back(symbol, sessions):
            r = one_round(symbol, target, cycle_id=cycle)
            if not r:
                continue
            out.append(r)
            if write:
                journal.append("forecast_resolved", {
                    "symbol": r.symbol, "expiry": r.target.isoformat(),
                    "lo": r.lo, "hi": r.hi, "p": r.p, "close": r.close,
                    "inside": r.inside, "source": "practice", "task": "fixed_band",
                    "reasoning": r.reasoning,
                    "brier_contribution": round(r.brier_contribution, 5)})
    return out
