"""Find thresholds that overrule the measurement.

Three times now a constant chosen by feel has quietly overridden a mechanism that
measures: a credit floor that refused every trade, a symbol list that excluded a
tradeable name, a delta band that rejected the search's best structure for being
too likely to win. Each was found by accident, by a person asking a question.

The shared signature is checkable. Gate 8 is the measured one: it derives the
probability of winning from live option deltas and compares it against the
breakeven implied by our own exit rules. So a hand-picked gate that keeps
refusing structures gate 8 approved is, by construction, substituting a guess for
a measurement. This walks the live surface and counts exactly that, per gate,
along with the expected value being discarded.

It cannot prove a threshold is right. It can show which thresholds are binding,
how much they cost, and which have never refused anything at all -- constants
carried along that nobody has tested because they never fire.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from saadhak.broker import account as acct
from saadhak.broker.data import chain, latest_price
from saadhak.config import settings
from saadhak.engine import gates as G
from saadhak.engine.decide import expiries
from saadhak.engine.monitor import attach_exit_rules
from saadhak.engine.select import search
from saadhak.engine.sizing import size_structure

# Gates that describe the world rather than our preferences. Refusals here are
# facts about the session, not evidence of a badly chosen constant.
ENVIRONMENTAL = {1, 10, 11, 16, 17}
# Gates whose whole purpose is to refuse: risk appetite, deliberately chosen.
RISK_APPETITE = {2, 4, 5, 6, 12}
MEASURED = 8


@dataclass
class GateStat:
    n: int
    name: str
    refusals: int = 0
    refused_while_measured_passed: int = 0
    best_score_refused: float = 0.0
    examples: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        if self.n in ENVIRONMENTAL:
            return "environmental"
        if self.n in RISK_APPETITE:
            return "risk appetite"
        if self.n == MEASURED:
            return "measured"
        return "threshold"

    @property
    def verdict(self) -> str:
        if self.kind in ("environmental", "measured"):
            return ""
        if self.refusals == 0:
            return "never fires — untested"
        if self.kind == "threshold" and self.refused_while_measured_passed:
            return (f"OVERRULES THE MEASUREMENT on "
                    f"{self.refused_while_measured_passed}")
        return "binding"


@dataclass
class Audit:
    considered: int = 0
    stats: dict[int, GateStat] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)

    @property
    def suspects(self) -> list[GateStat]:
        return [s for s in self.stats.values()
                if s.kind == "threshold" and s.refused_while_measured_passed]

    @property
    def untested(self) -> list[GateStat]:
        return [s for s in self.stats.values()
                if s.kind == "threshold" and s.refusals == 0]


def run(symbols: list[str], per_symbol: int = 12) -> Audit:
    s = settings()
    a = acct.get_account()
    clock = acct.get_clock()
    au = Audit(symbols=list(symbols))

    for symbol in symbols:
        try:
            spot = latest_price(symbol)
            chains = {e: chain(symbol, e, spot=spot, strike_window_pct=0.05)
                      for e in expiries(symbol, s.max_dte)}
            srch = search(chains)
        except Exception:
            continue

        ranked = sorted(srch.candidates, key=lambda c: c.score, reverse=True)[:per_symbol]
        for cand in ranked:
            st = cand.structure
            qty, _ = size_structure(st, a.equity, brier=None)
            st.qty = max(qty, 1)
            attach_exit_rules(st)
            ctx = G.GateContext(
                structure=st, equity=a.equity, qty=qty,
                market_open=bool(clock["is_open"]),
                minutes_since_open=acct.minutes_since_open(),
                minutes_to_close=acct.minutes_to_close(), spot=spot,
                daily_pl_pct=a.daily_pl_pct, whitelist=symbols)
            results = G.evaluate(ctx)
            au.considered += 1

            measured_ok = next(r.ok for r in results if r.n == MEASURED)
            for r in results:
                stat = au.stats.setdefault(r.n, GateStat(r.n, r.name))
                if r.ok:
                    continue
                stat.refusals += 1
                if measured_ok and stat.kind == "threshold":
                    stat.refused_while_measured_passed += 1
                    stat.best_score_refused = max(stat.best_score_refused, cand.score)
                    if len(stat.examples) < 3:
                        stat.examples.append(f"{st.describe()} — {r.reason}")
    return au
