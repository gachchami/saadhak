"""Market data: option chain snapshots with greeks (Alpaca's, or ours), stock quotes, news."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from saadhak import greeks as bs
from saadhak.broker.client import data
from saadhak.config import settings

RISK_FREE = 0.04


@dataclass(frozen=True)
class Contract:
    symbol: str
    underlying: str
    kind: str          # call | put
    strike: float
    expiry: date
    bid: float
    ask: float
    quote_ts: datetime
    delta: float | None
    iv: float | None
    volume: int
    greeks_source: str  # alpaca | computed | none

    @property
    def mid(self) -> float:
        return round((self.bid + self.ask) / 2.0, 2)

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def spread_pct(self) -> float:
        return self.spread / self.mid if self.mid > 0 else 1.0

    @property
    def quote_age_s(self) -> float:
        return (datetime.now(UTC) - self.quote_ts).total_seconds()

    @property
    def dte(self) -> int:
        return (self.expiry - datetime.now(UTC).date()).days

    @property
    def abs_delta(self) -> float:
        return abs(self.delta) if self.delta is not None else float("nan")


def last_trade(symbol: str) -> tuple[float, datetime]:
    """The most recent print, which outside regular hours is an extended-hours one."""
    s = settings()
    d = data(f"/v2/stocks/{symbol}/trades/latest", params={"feed": s.stock_feed})["trade"]
    return float(d["p"]), datetime.fromisoformat(d["t"].replace("Z", "+00:00"))


def session_close(symbol: str) -> float | None:
    """The last regular-session close, which is the clock the option chain is on."""
    s = settings()
    d = data(f"/v2/stocks/{symbol}/bars",
             params={"timeframe": "1Day", "feed": s.stock_feed, "limit": 1})
    bars = d.get("bars") or []
    return float(bars[-1]["c"]) if bars else None


def latest_price(symbol: str, *, market_open: bool | None = None) -> float:
    """Spot, on the same clock as the option quotes we compare it against.

    Option quotes stop updating at the close, so pairing them with an
    extended-hours print silently mixes two different moments. After an earnings
    release that gap is the entire move: on 2 Sep, SNOW last traded at $368
    after hours against a $306.86 close, so a straddle priced at the close read
    as 19% of spot when it was really 23%. During regular hours the two agree
    and the last trade is used; outside them we fall back to the close.
    """
    price, _ = last_trade(symbol)
    if market_open is None:
        try:
            from saadhak.broker.account import get_clock
            market_open = bool(get_clock()["is_open"])
        except Exception:
            market_open = True
    if market_open:
        return price
    return session_close(symbol) or price


def _parse_occ(sym: str) -> tuple[str, date, str, float]:
    """AAPL260904C00302500 -> (AAPL, 2026-09-04, call, 302.5)"""
    i = 0
    while i < len(sym) and not sym[i].isdigit():
        i += 1
    root, rest = sym[:i], sym[i:]
    expiry = date(2000 + int(rest[0:2]), int(rest[2:4]), int(rest[4:6]))
    kind = "call" if rest[6] == "C" else "put"
    strike = int(rest[7:15]) / 1000.0
    return root, expiry, kind, strike


def chain(underlying: str, expiry: date, kind: str | None = None,
          spot: float | None = None, strike_window_pct: float = 0.08) -> list[Contract]:
    """Snapshots for one expiry, filtered to a window around spot to stay inside rate limits."""
    s = settings()
    spot = spot or latest_price(underlying)
    params = {
        "feed": s.options_feed,
        "expiration_date": expiry.isoformat(),
        "strike_price_gte": round(spot * (1 - strike_window_pct), 2),
        "strike_price_lte": round(spot * (1 + strike_window_pct), 2),
        "limit": 1000,
    }
    if kind:
        params["type"] = kind
    out: list[Contract] = []
    token = None
    while True:
        if token:
            params["page_token"] = token
        d = data(f"/v1beta1/options/snapshots/{underlying}", params=params)
        for sym, snap in (d.get("snapshots") or {}).items():
            c = _to_contract(sym, snap, spot)
            if c:
                out.append(c)
        token = d.get("next_page_token")
        if not token:
            break
    return sorted(out, key=lambda c: (c.kind, c.strike))


def _to_contract(sym: str, snap: dict, spot: float) -> Contract | None:
    q = snap.get("latestQuote") or {}
    bid, ask = float(q.get("bp") or 0), float(q.get("ap") or 0)
    if ask <= 0:
        return None
    root, expiry, kind, strike = _parse_occ(sym)
    ts = q.get("t")
    quote_ts = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(UTC)

    g, iv, src = snap.get("greeks"), snap.get("impliedVolatility"), "alpaca"
    delta = float(g["delta"]) if g and g.get("delta") is not None else None
    if delta is None:
        mid = (bid + ask) / 2.0
        t = max((expiry - datetime.now(UTC).date()).days, 0) / 365.0
        t = max(t, 1 / 365.0 / 6.5)  # never zero on expiry day
        solved = bs.implied_vol(mid, spot, strike, t, RISK_FREE, kind)
        if solved:
            delta = bs.greeks(spot, strike, t, RISK_FREE, solved, kind)["delta"]
            iv, src = solved, "computed"
        else:
            src = "none"
    day = snap.get("dailyBar") or {}
    return Contract(
        symbol=sym, underlying=root, kind=kind, strike=strike, expiry=expiry,
        bid=bid, ask=ask, quote_ts=quote_ts,
        delta=delta, iv=float(iv) if iv else None,
        volume=int(day.get("v") or 0), greeks_source=src,
    )


def nearest_expiry(underlying: str, max_dte: int) -> date | None:
    """The soonest tradable expiry within max_dte, from the contracts endpoint."""
    from saadhak.broker.client import trading
    today = datetime.now(UTC).date()
    d = trading("/options/contracts", params={
        "underlying_symbols": underlying, "status": "active", "limit": 10000,
        "expiration_date_gte": today.isoformat(),
        "expiration_date_lte": date.fromordinal(today.toordinal() + max_dte).isoformat(),
    })
    days = {c["expiration_date"] for c in (d.get("option_contracts") or [])}
    return min((date.fromisoformat(x) for x in days), default=None)


def news(symbols: list[str], limit: int = 10) -> list[dict]:
    d = data("/v1beta1/news", params={"symbols": ",".join(symbols), "limit": limit})
    return d.get("news") or []
