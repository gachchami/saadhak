"""Discover what is tradeable, instead of typing a list.

The universe was nine symbols I chose. Alpaca's most-active screener is no help
here because it ranks by share volume, which surfaces penny stocks and warrants
that have no options at all. The right question is not "what is busy" but "what
has options expiring inside our window", and the contracts endpoint answers it
directly: on 2 September, 691 underlyings listed options for that Friday.

Listing count stands in for market interest, since Alpaca does not populate open
interest on the contracts endpoint. It is only a shortlist; the screen still has
to prove each name is liquid and clears the expectancy gate. Cash-settled index
options are excluded: SPX and friends are European and settle to a print rather
than to shares, so the assignment reasoning in our exit rules does not apply.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from saadhak.broker.client import trading

def live_expiries(expiries: list[date], *, market_open: bool | None = None) -> list[date]:
    """Drop expiries that have already settled.

    Today's contracts are tradeable right up to the close and worthless a minute
    later. Screening after hours without this reads terminal quotes on dead
    contracts as if they were a market.
    """
    today = datetime.now(UTC).date()
    if market_open is None:
        try:
            from saadhak.broker.account import get_clock
            market_open = bool(get_clock()["is_open"])
        except Exception:
            market_open = True
    out = []
    for e in expiries:
        if e < today:
            continue
        if e == today and not market_open:
            continue          # expired at this afternoon's close
        out.append(e)
    return out


# Cash-settled index options: European exercise, settle in cash, no assignment.
# Our proximity and time-stop rules are written for deliverable contracts.
CASH_SETTLED = {"SPX", "SPXW", "XSP", "NDX", "NDXP", "RUT", "RUTW", "VIX", "VIXW",
                "DJX", "OEX", "XEO", "MRUT", "MXEA", "MXEF"}

# Leveraged and inverse products: their options price a daily-rebalanced return,
# so delta means something different and our expectancy model does not hold.
LEVERAGED_HINTS = ("2X", "3X")
LEVERAGED = {"TQQQ", "SQQQ", "SOXL", "SOXS", "TSLL", "TSLQ", "NVDL", "NVD", "AMDL",
             "SPXL", "SPXS", "UPRO", "SPXU", "TNA", "TZA", "LABU", "LABD",
             "NUGT", "DUST", "JNUG", "JDST", "AGQ", "UVXY", "SVXY", "BITO", "BITX"}


@dataclass
class Discovered:
    expiry: date
    counts: Counter = field(default_factory=Counter)
    excluded: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.counts)

    def top(self, n: int) -> list[str]:
        return [s for s, _ in self.counts.most_common(n)]


_CACHE: dict[date, Discovered] = {}


def discover(expiry: date, *, max_pages: int = 12, use_cache: bool = True) -> Discovered:
    """Every underlying listing options for `expiry`, ranked by contracts listed."""
    if use_cache and expiry in _CACHE:
        return _CACHE[expiry]

    d = Discovered(expiry)
    token, pages = None, 0
    while pages < max_pages:
        params = {"expiration_date": expiry.isoformat(), "status": "active",
                  "limit": 10000}
        if token:
            params["page_token"] = token
        resp = trading("/options/contracts", params=params)
        for c in resp.get("option_contracts") or []:
            sym = c["underlying_symbol"]
            if sym in CASH_SETTLED:
                d.excluded[sym] = "cash-settled index option"
                continue
            if sym in LEVERAGED or any(h in sym for h in LEVERAGED_HINTS):
                d.excluded[sym] = "leveraged or inverse product"
                continue
            d.counts[sym] += 1
        pages += 1
        token = resp.get("next_page_token")
        if not token:
            break
    if use_cache:
        _CACHE[expiry] = d
    return d


def candidates(max_dte: int = 1, top: int = 30) -> tuple[list[str], Discovered | None]:
    """Shortlist for the screen: the most-listed names on the nearest expiry."""
    from datetime import timedelta
    today = datetime.now(UTC).date()
    days = live_expiries([today + timedelta(days=i) for i in range(max_dte + 1)])
    for day in days:
        d = discover(day)
        if d.total:
            return d.top(top), d
    return [], None
