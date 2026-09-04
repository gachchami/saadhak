"""Record what the numbers rest on.

This account is on Alpaca's free data tier: stock quotes from IEX alone rather
than the consolidated NBBO, option quotes from the indicative feed because the
OPRA agreement is not signed, and consolidated data delayed fifteen minutes. On
liquid index ETFs during regular hours that is close enough to trade on. It is
not close enough to be quiet about.

Tonight it mattered. AVGO fell to $344 and recovered to $373 during its earnings
call, and our last visible print was sixteen minutes stale and on the wrong side
of the reversal. Trading was never at risk, because the gates only fire during
regular hours, but every conclusion drawn after the close was drawn blind.

So each decision carries the provenance of its inputs, and a judge or a future
reader can see how good they were rather than having to assume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from saadhak.config import settings

FEED_QUALITY = {
    "iex": "single exchange (IEX), not consolidated NBBO",
    "sip": "consolidated NBBO",
    "delayed_sip": "consolidated, delayed 15 minutes",
    "indicative": "indicative option quotes; OPRA agreement not signed",
    "opra": "OPRA consolidated option quotes",
}


@dataclass
class Provenance:
    stock_feed: str
    option_feed: str
    quote_ages_s: list[float] = field(default_factory=list)
    market_open: bool = True
    captured_at: str = ""

    @property
    def worst_quote_age_s(self) -> float:
        return max(self.quote_ages_s) if self.quote_ages_s else 0.0

    @property
    def degraded(self) -> bool:
        """True when the inputs are too stale or too partial to reason from."""
        if not self.market_open:
            return True
        return self.worst_quote_age_s > settings().max_quote_age_s

    @property
    def note(self) -> str:
        bits = [f"stock: {FEED_QUALITY.get(self.stock_feed, self.stock_feed)}",
                f"options: {FEED_QUALITY.get(self.option_feed, self.option_feed)}"]
        if self.quote_ages_s:
            bits.append(f"worst quote age {self.worst_quote_age_s:.0f}s")
        if not self.market_open:
            bits.append("market closed: quotes are terminal, not live")
        return "; ".join(bits)

    def to_dict(self) -> dict:
        return {"stock_feed": self.stock_feed, "option_feed": self.option_feed,
                "worst_quote_age_s": round(self.worst_quote_age_s, 1),
                "market_open": self.market_open, "degraded": self.degraded,
                "captured_at": self.captured_at, "note": self.note}


def capture(contracts=(), *, market_open: bool | None = None) -> Provenance:
    s = settings()
    if market_open is None:
        try:
            from saadhak.broker.account import get_clock
            market_open = bool(get_clock()["is_open"])
        except Exception:
            market_open = True
    return Provenance(
        stock_feed=s.stock_feed, option_feed=s.options_feed,
        quote_ages_s=[c.quote_age_s for c in contracts],
        market_open=market_open,
        captured_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
