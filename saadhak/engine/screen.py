"""Which underlyings are worth trading today, decided by measurement.

The universe was previously a string literal someone typed. The reasons behind
it were real — index ETFs list daily expiries, quote tightly, and cannot report
earnings — but an untested reason is a preference, not a decision, and it cannot
notice when it stops being true.

The screen reuses the same expectancy search the engine already runs within a
symbol, and runs it across symbols. The question it answers is the one that
matters: where on today's surface is the best expected value per dollar at risk?
A name that lists no short-dated expiry, quotes too wide, or reports earnings is
excluded with a stated reason rather than silently ranked last.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from saadhak.broker.client import trading
from saadhak.broker.data import chain, latest_price
from saadhak.config import settings
from saadhak.engine.events import earnings_soon
from saadhak.engine.select import search
from saadhak.witness import journal

# Kept only as the fallback when discovery is unavailable. The live universe
# comes from engine/universe.py, which reads what actually lists options in our
# window rather than what someone once typed here.
FALLBACK_UNIVERSE = ("SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "NVDA", "AMZN", "META")
DEFAULT_UNIVERSE = FALLBACK_UNIVERSE   # backwards compatibility for callers/tests


@dataclass
class Screened:
    symbol: str
    tradeable: bool
    reason: str
    spot: float = 0.0
    expiries: list[date] = field(default_factory=list)
    best_score: float = 0.0
    best_credit: float = 0.0
    best_win_prob: float = 0.0
    viable: int = 0
    considered: int = 0

    def row(self) -> dict:
        return {"symbol": self.symbol, "tradeable": self.tradeable,
                "reason": self.reason, "spot": self.spot,
                "expiries": [e.isoformat() for e in self.expiries],
                "viable": self.viable, "considered": self.considered,
                "best_score": round(self.best_score, 5),
                "best_credit": self.best_credit,
                "best_win_prob": round(self.best_win_prob, 4)}


def _expiries(symbol: str, max_dte: int) -> list[date]:
    today = datetime.now(UTC).date()
    d = trading("/options/contracts", params={
        "underlying_symbols": symbol, "status": "active", "limit": 10000,
        "expiration_date_gte": today.isoformat(),
        "expiration_date_lte": (today + timedelta(days=max_dte)).isoformat()})
    from saadhak.engine.universe import live_expiries
    return live_expiries(sorted({date.fromisoformat(c["expiration_date"])
                                 for c in (d.get("option_contracts") or [])}))


def screen_one(symbol: str) -> Screened:
    s = settings()
    try:
        ev = earnings_soon(symbol, datetime.now(UTC).date())
        if ev.has_event:
            return Screened(symbol, False, f"earnings: {ev.reason}")

        exps = _expiries(symbol, s.max_dte)
        if not exps:
            return Screened(symbol, False,
                            f"no expiry within {s.max_dte} DTE (needs daily or next-day options)")

        spot = latest_price(symbol)
        chains = {e: chain(symbol, e, spot=spot, strike_window_pct=0.05) for e in exps}
        if not any(chains.values()):
            return Screened(symbol, False, "no quoted contracts near the money",
                            spot=spot, expiries=exps)

        srch = search(chains)
        if not srch.viable:
            return Screened(symbol, False,
                            "no structure clears the expectancy gate today",
                            spot=spot, expiries=exps, considered=srch.considered)

        best = srch.best
        return Screened(symbol, True, "tradeable", spot=spot, expiries=exps,
                        best_score=best.score, best_credit=best.structure.net_credit,
                        best_win_prob=best.expectancy.win_prob,
                        viable=len(srch.viable), considered=srch.considered)
    except Exception as e:
        return Screened(symbol, False, f"screen failed: {type(e).__name__}: {e}")


def screen(universe: list[str] | None = None, *, top: int = 3,
           journal_write: bool = True, shortlist: int = 14) -> list[Screened]:
    """Rank the universe by the best expected value per dollar at risk.

    With no universe given, the candidates are discovered from the options market
    itself: every underlying listing contracts in our expiry window, ranked by
    how many it lists, which stands in for market interest.
    """
    names = universe
    discovered = None
    if names is None:
        try:
            from saadhak.engine.universe import candidates
            names, discovered = candidates(max_dte=settings().max_dte, top=shortlist)
        except Exception:
            names = None
        if not names:
            names = list(FALLBACK_UNIVERSE)
    results = [screen_one(n) for n in names]
    results.sort(key=lambda r: (r.tradeable, r.best_score), reverse=True)
    if journal_write:
        journal.append("screen", {
            "universe": names, "top": top,
            "discovered_from_options_market": bool(discovered),
            "underlyings_listing_options": discovered.total if discovered else None,
            "chosen": [r.symbol for r in results if r.tradeable][:top],
            "results": [r.row() for r in results]})
    return results


def tradeable_symbols(universe: list[str] | None = None, top: int = 3,
                      shortlist: int = 14) -> list[str]:
    return [r.symbol for r in screen(universe, top=top, shortlist=shortlist)
            if r.tradeable][:top]
