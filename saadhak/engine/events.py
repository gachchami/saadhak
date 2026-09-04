"""Scheduled-event detection. Safety must not depend on a language model.

Book A's expectancy model estimates the probability of finishing out of the money
from option deltas. That estimate assumes prices diffuse. An earnings release is
a gap: the stock can jump straight through both strikes overnight, and delta
badly understates that. So the number the gate trusts is known to be wrong
exactly when a catalyst sits inside the holding window, and the correct response
is to refuse the trade rather than to price it with a model that does not apply.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

from saadhak.broker.data import news

# Anything earnings-shaped. Used only to notice that the subject is in play.
EARNINGS_PATTERNS = (
    r"\bq[1-4]\b.{0,30}\bearnings\b", r"\bearnings\b.{0,30}\b(today|after the (bell|close))\b",
    r"\breports?\b.{0,20}\bearnings\b", r"\bearnings\b.{0,20}\b(preview|call|release|results)\b",
    r"\bahead of\b.{0,20}\bearnings\b", r"\bfiscal\b.{0,20}\b(q[1-4]|quarter)\b.{0,30}\bresults\b",
)

# Published numbers. These only appear once the results are out, so they are the
# signal that the gap has already happened rather than still lying ahead.
RESULT_PATTERNS = (
    r"\beps\b.{0,20}\$", r"\$[\d.]+.{0,20}\beps\b",
    r"\b(beats?|misses|missed|tops|topped)\b.{0,30}\b(estimate|consensus|expectations)\b",
    r"\b(raises?|lowers?|cuts?|lifts?)\b.{0,30}\bguidance\b",
    r"\bsees\b.{0,10}\bq[1-4]\b", r"\bq[1-4]\b.{0,25}\b(adj\.?|gaap)\b.{0,10}\beps\b",
    r"\breported\b.{0,25}\b(revenue|sales|earnings|profit)\b",
    r"\b(revenue|sales)\b.{0,20}\$[\d.]+\s*(b|m|billion|million)\b",
)

# Language that only makes sense before the release.
PREVIEW_PATTERNS = (
    r"\bahead of\b", r"\bpreview\b", r"\bexpected to report\b", r"\bwill report\b",
    r"\bset to report\b", r"\blikely to report\b", r"\bwhat to expect\b",
    r"\brevise\b.{0,20}\bforecasts?\b", r"\bforecasters?\b",
)


@dataclass(frozen=True)
class EventCheck:
    has_event: bool
    kind: str
    evidence: list[str]
    reason: str
    reported: bool = False      # results are published; the gap is behind us


def earnings_soon(symbol: str, through: date, *, limit: int = 12) -> EventCheck:
    """Look for earnings chatter in recent headlines for this symbol.

    Deliberately conservative: headlines cannot prove an event is absent, so a
    hit refuses the trade while a miss only means we found nothing. Index ETFs
    have no earnings and are exempt.
    """
    if symbol in {"SPY", "QQQ", "IWM", "DIA"}:
        return EventCheck(False, "", [], "index ETF, no earnings")
    try:
        items = news([symbol], limit=limit)
    except Exception as e:
        return EventCheck(False, "", [], f"news unavailable: {e}")

    today = datetime.now(UTC).date()
    hits, results, previews = [], [], []
    for n in items:
        head = (n.get("headline") or "").lower()
        created = (n.get("created_at") or "")[:10]
        try:
            if (today - date.fromisoformat(created)).days > 3:
                continue
        except ValueError:
            pass
        line = f"{created}: {n.get('headline','')[:110]}"
        if any(re.search(p, head) for p in RESULT_PATTERNS):
            results.append(line)
            hits.append(line)
        elif any(re.search(p, head) for p in EARNINGS_PATTERNS + PREVIEW_PATTERNS):
            previews.append(line)
            hits.append(line)

    if not hits:
        return EventCheck(False, "", [], "no earnings signal in recent headlines")

    # Published numbers mean the gap has already happened. What remains is
    # ordinary volatility, and gate 8 prices that correctly: the deltas it reads
    # come from post-announcement quotes with the uncertainty already collapsed
    # out of them. Continuing to refuse here would be blocking a risk that no
    # longer exists.
    if results:
        return EventCheck(False, "earnings_reported", results[:3],
                          f"{symbol} has reported; the gap is behind us and current "
                          f"deltas already price what is left",
                          reported=True)

    return EventCheck(True, "earnings", previews[:3],
                      f"{symbol} reports within the holding window; a gap breaks "
                      f"the delta-based expectancy model")
