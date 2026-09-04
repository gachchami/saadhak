"""The nineteen gates. Every order passes all of them or is refused with a readable reason.

Gates are pure functions of a GateContext so they can be unit-tested without a broker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, UTC

from saadhak.config import settings
from saadhak.engine.structures import Structure


@dataclass
class GateContext:
    structure: Structure
    equity: float
    qty: int
    market_open: bool
    minutes_since_open: float | None
    minutes_to_close: float | None
    spot: float
    open_structures: int = 0
    same_underlying: int = 0
    open_risk: float = 0.0
    daily_pl_pct: float = 0.0
    drawdown_pct: float = 0.0
    whitelist: list[str] = field(default_factory=list)
    event_in_window: bool = False
    event_reason: str = ""
    reconciled: bool = True
    reconcile_note: str = ""
    regime_blocked: bool = False
    regime_reason: str = ""
    correlated_blocked: bool = False
    correlated_reason: str = ""
    halted: bool = False
    is_exit: bool = False


@dataclass(frozen=True)
class GateResult:
    n: int
    name: str
    ok: bool
    reason: str

    def __str__(self) -> str:
        return f"{'PASS' if self.ok else 'FAIL'} {self.n:02d} {self.name}: {self.reason}"


def _g(n, name, ok, reason) -> GateResult:
    return GateResult(n, name, ok, reason)


def evaluate(ctx: GateContext) -> list[GateResult]:
    s = settings()
    st = ctx.structure
    out: list[GateResult] = []

    # 1 market hours
    if not ctx.market_open:
        out.append(_g(1, "market_hours", False, "market is closed"))
    elif ctx.is_exit:
        out.append(_g(1, "market_hours", True, "exit exempt from window rules"))
    else:
        mso, mtc = ctx.minutes_since_open, ctx.minutes_to_close
        ok = (mso is None or mso >= 15) and (mtc is None or mtc >= 15)
        out.append(_g(1, "market_hours", ok,
                      f"open {mso:.0f}m, {mtc:.0f}m to close" if mso is not None and mtc is not None
                      else "clock unavailable"))

    # 2 whitelist
    ok = not ctx.whitelist or st.underlying in ctx.whitelist
    out.append(_g(2, "whitelist", ok, f"{st.underlying} {'on' if ok else 'not on'} the whitelist"))

    # 3 defined risk
    sells = [l for l in st.legs if l.side == "sell"]
    buys = [l for l in st.legs if l.side == "buy"]
    covered = len(buys) >= len(sells) and len(st.legs) <= 4
    same_expiry = len({l.contract.expiry for l in st.legs}) == 1
    out.append(_g(3, "defined_risk", covered and same_expiry,
                  f"{len(sells)} short / {len(buys)} long, {len(st.legs)} legs, single expiry={same_expiry}"))

    # 4 max loss per structure
    cap_pct = s.max_loss_pct_book_a if st.book == "A" else s.max_loss_pct_book_b
    cap = ctx.equity * cap_pct
    risk = st.max_loss_per_unit * max(ctx.qty, 1)
    out.append(_g(4, "max_loss", risk <= cap,
                  f"${risk:,.0f} vs cap ${cap:,.0f} ({cap_pct:.1%} of equity)"))

    # 5 portfolio caps
    prisk = ctx.open_risk + risk
    pcap = ctx.equity * s.max_portfolio_risk_pct
    ok = (prisk <= pcap and ctx.open_structures < s.max_structures
          and ctx.same_underlying < s.max_per_underlying)
    out.append(_g(5, "portfolio_caps", ok,
                  f"risk ${prisk:,.0f}/${pcap:,.0f}, {ctx.open_structures}/{s.max_structures} structures, "
                  f"{ctx.same_underlying}/{s.max_per_underlying} on {st.underlying}"))

    # 6 loss halts
    ok = ctx.daily_pl_pct > -s.daily_loss_halt_pct and ctx.drawdown_pct < s.total_drawdown_halt_pct
    out.append(_g(6, "loss_halts", ok and not ctx.halted,
                  f"daily {ctx.daily_pl_pct:+.2%} (halt {-s.daily_loss_halt_pct:.0%}), "
                  f"drawdown {ctx.drawdown_pct:.2%} (halt {s.total_drawdown_halt_pct:.0%})"))

    # 7 liquidity, per side. Requiring a bid on every leg refused executable
    # trades: the far wing of a condor is bought at the ask and routinely has no
    # bid at all, which is normal for cheap protection and no obstacle to filling.
    # What each leg needs is a price on the side we actually cross.
    bad = []
    for l in st.legs:
        c = l.contract
        if l.side == "sell" and c.bid <= 0:
            bad.append(f"{c.symbol} no bid to sell into")
        elif l.side == "buy" and c.ask <= 0:
            bad.append(f"{c.symbol} no ask to buy")
        elif (c.mid > 0 and c.spread > s.max_spread_abs
              and c.spread_pct > s.max_spread_pct):
            bad.append(f"{c.symbol} spread {c.spread_pct:.0%}")
        elif c.quote_age_s > s.max_quote_age_s and ctx.market_open:
            bad.append(f"{c.symbol} quote {c.quote_age_s:.0f}s old")
    # Volume matters on the legs we are short: those are the ones we must buy
    # back, possibly in a hurry.
    for l in st.short_legs:
        if l.contract.volume < 100:
            bad.append(f"{l.contract.symbol} volume {l.contract.volume}")
    out.append(_g(7, "liquidity", not bad, "; ".join(bad) if bad else "all legs tradeable"))

    # 8 expectancy: does this structure win more often than the exit rules require?
    if st.is_credit and st.width > 0:
        from saadhak.engine.expectancy import evaluate as expectancy_of
        e = expectancy_of(st)
        out.append(_g(8, "expectancy", e.ok, e.reason))
    else:
        out.append(_g(8, "expectancy", True, "not a credit structure"))

    # 9 delta data quality. This was a hand-picked 0.08-0.15 band, which both
    # duplicated gate 8 (the same deltas, via P(win)) and contradicted the search,
    # whose best-scoring structure was routinely refused for being too far out of
    # the money -- that is, for being too likely to win. What gate 8 genuinely
    # needs is that the deltas it reasons about exist and come from a known source.
    missing = [l.contract.symbol for l in st.short_legs if l.contract.delta is None]
    unsourced = [l.contract.symbol for l in st.short_legs
                 if l.contract.greeks_source not in ("alpaca", "computed")]
    ok = not missing and not unsourced
    detail = ("short deltas " + ", ".join(
        f"{abs(l.contract.delta):.3f} ({l.contract.greeks_source})" for l in st.short_legs)
        if ok else f"missing deltas: {missing or unsourced}")
    out.append(_g(9, "delta_data", ok, detail))

    # 10 dte
    dte = (st.expiry - datetime.now(UTC).date()).days
    limit = s.max_dte if st.book == "A" else 7
    out.append(_g(10, "dte", 0 <= dte <= limit, f"{dte} DTE (max {limit})"))

    # 19 correlation: is this a second position, or the same one again?
    if not ctx.is_exit and ctx.correlated_blocked:
        out.append(_g(19, "correlation", False, ctx.correlated_reason))
    else:
        out.append(_g(19, "correlation", True, ctx.correlated_reason or "uncorrelated"))

    # 10b regime: has this exact trade just failed, repeatedly, for one reason?
    if not ctx.is_exit and ctx.regime_blocked:
        out.append(_g(18, "regime", False, ctx.regime_reason))
    else:
        out.append(_g(18, "regime", True, ctx.regime_reason or "no adverse run"))

    # 11 event guard: a gap invalidates the delta-based expectancy in gate 8
    if ctx.event_in_window and st.book == "A":
        out.append(_g(11, "event_guard", False, ctx.event_reason or "event inside holding window"))
    else:
        out.append(_g(11, "event_guard", True, ctx.event_reason or "no event in window"))

    # 12 sizeable
    out.append(_g(12, "sizeable", ctx.qty >= 1, f"qty {ctx.qty}"))

    # 13 idempotency
    cid = client_order_id(st)
    out.append(_g(13, "idempotent_id", bool(cid), f"client_order_id {cid[:16]}..."))

    # 14 limit discipline (structural: we never build market orders)
    out.append(_g(14, "limit_only", True, "limit at mid, 3-step walk, never market"))

    # 15 exit rules attached
    ok = all(k in st.meta for k in ("tp_price", "sl_price")) or ctx.is_exit
    out.append(_g(15, "exit_rules", ok,
                  "TP/SL/time attached at entry" if ok else "exit rules not attached"))

    # 16 reconciliation
    out.append(_g(16, "reconciled", ctx.reconciled,
                  ctx.reconcile_note or ("CLI and REST agree" if ctx.reconciled
                                         else "CLI and REST disagree")))

    # 17 kill switch
    from pathlib import Path
    stopped = Path("STOP").exists()
    out.append(_g(17, "kill_switch", not stopped, "STOP file present" if stopped else "no STOP file"))

    return out


def passed(results: list[GateResult]) -> bool:
    return all(r.ok for r in results)


def failures(results: list[GateResult]) -> list[GateResult]:
    return [r for r in results if not r.ok]


def client_order_id(st: Structure, cycle_id: str = "") -> str:
    import hashlib
    key = f"{cycle_id}|{st.underlying}|{st.expiry}|{st.kind}|" + ",".join(
        sorted(l.contract.symbol for l in st.legs)) + f"|{st.qty}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]
