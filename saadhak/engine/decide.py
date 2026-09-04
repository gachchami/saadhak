"""One decision: search the surface, size the winner, run the gates, journal it all."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from saadhak.broker import account as acct
from saadhak.broker.client import trading
from saadhak.broker.data import chain, latest_price
from saadhak.broker.provenance import capture as capture_provenance
from saadhak.config import settings
from saadhak.engine import gates as G
from saadhak.engine.events import earnings_soon
from saadhak.engine.correlation import check as correlation_check
from saadhak.engine.regime import check as regime_check
from saadhak.engine.monitor import attach_exit_rules
from saadhak.engine.select import Search, search
from saadhak.engine.sizing import size_structure
from saadhak.engine.structures import Structure
from saadhak.practitioner.review import Verdict, review
from saadhak.witness import journal
from saadhak.witness.positions import open_structures
from saadhak.witness.calibration import current as calibration_now
from saadhak.witness.reconcile import reconcile


@dataclass
class Decision:
    cycle_id: str
    symbol: str
    spot: float
    search: Search
    structure: Structure | None
    qty: int
    sizing: dict
    gates: list
    accepted: bool
    reason: str
    verdict: Verdict | None = None


def expiries(symbol: str, max_dte: int) -> list[date]:
    today = datetime.now(UTC).date()
    d = trading("/options/contracts", params={
        "underlying_symbols": symbol, "status": "active", "limit": 10000,
        "expiration_date_gte": today.isoformat(),
        "expiration_date_lte": (today + timedelta(days=max_dte)).isoformat()})
    from saadhak.engine.universe import live_expiries
    return live_expiries(sorted({date.fromisoformat(c["expiration_date"])
                                 for c in (d.get("option_contracts") or [])}))


def decide(symbol: str, *, book: str = "A", brier: float | None = None,
           cycle_id: str | None = None) -> Decision:
    """One decision. brier defaults to the desk's measured calibration."""
    s = settings()
    cycle_id = cycle_id or f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    a = acct.get_account()
    spot = latest_price(symbol)
    clock = acct.get_clock()

    chains = {e: chain(symbol, e, spot=spot, strike_window_pct=0.05)
              for e in expiries(symbol, s.max_dte)}
    srch = search(chains, book=book)
    prov = capture_provenance([c for cs in chains.values() for c in cs],
                              market_open=bool(clock["is_open"]))

    journal.append("search", {
        "provenance": prov.to_dict(),
        "cycle_id": cycle_id, "symbol": symbol, "spot": spot,
        "considered": srch.considered, "distinct": len(srch.candidates),
        "viable": len(srch.viable), "top": srch.journal_rows(8)})

    best = srch.best
    if not best:
        return Decision(cycle_id, symbol, spot, srch, None, 0, {}, [], False,
                        "no structure on the surface has positive expectancy")

    st = best.structure
    ev = earnings_soon(symbol, st.expiry) if s.earnings_guard else \
        __import__("saadhak.engine.events", fromlist=["EventCheck"]).EventCheck(False, "", [], "guard off")
    open_pos = acct.option_positions()
    from saadhak.broker.orders import open_orders
    pending = len(open_orders())
    open_risk = 0.0
    cal = calibration_now()
    if brier is None:
        brier = cal.brier                      # measured, not assumed
    rec = reconcile()
    reg = regime_check(symbol, equity=a.equity)
    held = [st.underlying for st in open_structures()]
    corr = correlation_check(symbol, [h for h in held if h != symbol])
    qty, why = size_structure(st, a.equity, brier=brier, open_risk=open_risk)
    why["calibration"] = cal.verdict
    st.qty = max(qty, 1)
    attach_exit_rules(st)

    ctx = G.GateContext(
        structure=st, equity=a.equity, qty=qty, market_open=bool(clock["is_open"]),
        minutes_since_open=acct.minutes_since_open(),
        minutes_to_close=acct.minutes_to_close(), spot=spot,
        open_structures=len(open_pos) // 4,
        same_underlying=sum(1 for p in open_pos if p["symbol"].startswith(symbol)) // 4,
        open_risk=open_risk, daily_pl_pct=a.daily_pl_pct, whitelist=s.symbols,
        event_in_window=ev.has_event, event_reason=ev.reason,
        reconciled=rec.ok, reconcile_note=rec.summary)
    results = G.evaluate(ctx)
    ok = G.passed(results)

    journal.append("gate_result", {
        "cycle_id": cycle_id, "structure": st.describe(), "underlying": symbol,
        "kind": st.kind, "qty": qty, "credit": st.net_credit,
        "max_loss": st.max_loss, "expectancy": best.row(),
        "gates": [{"n": r.n, "name": r.name, "ok": r.ok, "reason": r.reason} for r in results],
        "decision": "accept" if ok else "refuse", "sizing": why,
        "provenance": prov.to_dict()})

    if not ok:
        return Decision(cycle_id, symbol, spot, srch, st, qty, why, results, False,
                        "; ".join(r.name for r in G.failures(results)))

    # The practitioner reviews only what the gates already accepted. It can veto;
    # it cannot enlarge, resize or redirect the trade.
    v = review(st, spot, a.equity, best.expectancy.win_prob, cycle_id=cycle_id)
    if v.veto:
        journal.append("veto", {"cycle_id": cycle_id, "structure": st.describe(),
                                "reason": v.veto_reason, "model": v.model})
        return Decision(cycle_id, symbol, spot, srch, st, qty, why, results, False,
                        f"practitioner veto: {v.veto_reason}", v)

    return Decision(cycle_id, symbol, spot, srch, st, qty, why, results, True,
                    "all gates passed" + ("" if not v.consulted
                                          else f"; practitioner {v.summary}"), v)
