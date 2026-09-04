"""The autonomous agent: one process that opens, manages and closes positions
for the whole session without a human in the loop.

Entry windows are fixed and deliberate. The first 15 and last 15 minutes are
excluded by gate 1; inside the session the agent attempts an entry at each
window and otherwise only manages what is already open. Everything it does,
including every refusal, lands in the journal.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from saadhak.broker import account as acct
from saadhak.broker.orders import submit
from saadhak.config import settings
from saadhak.engine.decide import decide
from saadhak.engine.screen import tradeable_symbols
from saadhak.loop import monitor_once
from saadhak.witness import journal
from saadhak.witness.calibration import current as calibration_now
from saadhak.witness.reconcile import reconcile
from saadhak.witness.positions import open_structures

ENTRY_WINDOWS_MIN_AFTER_OPEN = (35, 120, 240)   # 10:05, 11:30, 13:30 ET


@dataclass
class AgentState:
    entries_attempted: set[tuple[str, int]] = field(default_factory=set)
    halted: bool = False
    halt_reason: str = ""
    cycles: int = 0

    def key(self, symbol: str, window: int) -> tuple[str, int]:
        return (f"{datetime.now(UTC).date()}:{symbol}", window)


def _log(msg: str) -> None:
    print(f"[{datetime.now(UTC):%H:%M:%S}Z] {msg}", flush=True)


def check_halts(state: AgentState) -> bool:
    """Account-level stops. Once halted, the agent manages exits only."""
    s = settings()
    if Path("STOP").exists():
        state.halted, state.halt_reason = True, "STOP file present"
    else:
        a = acct.get_account()
        if a.daily_pl_pct <= -s.daily_loss_halt_pct:
            state.halted = True
            state.halt_reason = f"daily loss {a.daily_pl_pct:.2%}"
        elif (a.equity / 100_000 - 1) <= -s.total_drawdown_halt_pct:
            state.halted = True
            state.halt_reason = f"drawdown {a.equity / 100_000 - 1:.2%}"
    if state.halted and state.halt_reason:
        journal.append("halt", {"reason": state.halt_reason})
        _log(f"HALTED: {state.halt_reason} (managing exits only)")
    return state.halted


def due_window(minutes_since_open: float | None) -> int | None:
    """The entry window we are currently inside, if any (15-minute tolerance)."""
    if minutes_since_open is None:
        return None
    for w in ENTRY_WINDOWS_MIN_AFTER_OPEN:
        if w <= minutes_since_open < w + 15:
            return w
    return None


def try_entry(symbol: str, window: int, state: AgentState, *, dry_run: bool) -> None:
    k = state.key(symbol, window)
    if k in state.entries_attempted:
        return
    state.entries_attempted.add(k)
    _log(f"entry window +{window}m: evaluating {symbol}")
    d = decide(symbol)
    if not d.accepted or not d.structure:
        _log(f"  REFUSED {symbol}: {d.reason}")
        return
    res = submit(d.structure, dry_run=dry_run, cycle_id=d.cycle_id)
    journal.append("order_submitted", {
        "cycle_id": d.cycle_id, "dry_run": dry_run, "body": res.body,
        "status": res.status, "order_id": res.order_id, "error": res.error})
    _log(f"  {res.status.upper()} {d.structure.describe()}"
         + (f" order {res.order_id}" if res.order_id else "")
         + (f" ERROR {res.error}" if res.error else ""))


def run(*, dry_run: bool = False, interval: int = 60,
        symbols: list[str] | None = None, universe: list[str] | None = None,
        top: int = 3) -> None:
    """symbols pins the list; otherwise the screen chooses it at each entry window."""
    s = settings()
    pinned = symbols
    symbols = symbols or s.symbols
    state = AgentState()
    _log(f"agent starting: symbols={symbols} dry_run={dry_run} interval={interval}s")

    # A desk with no score is unmeasured, not neutral. Earn one before sizing on it.
    cal = calibration_now()
    if cal.n == 0:
        _log("no calibration on record; practising on recent sessions first")
        try:
            from saadhak.practitioner.practice import run as practise
            rounds = practise(symbols, sessions=6)
            cal = calibration_now()
            _log(f"practice complete on {len(rounds)} forecasts: {cal.verdict}")
        except Exception as e:
            _log(f"practice failed ({e}); sizing falls back to the prior")
    else:
        _log(f"calibration: {cal.verdict}")

    # Check our own thresholds against the live surface before trading on them.
    # A constant that keeps refusing what the measurement approves is a guess
    # wearing the authority of a rule.
    try:
        from saadhak.engine.audit import run as audit_thresholds
        au = audit_thresholds(symbols or s.symbols, per_symbol=8)
        if au.suspects:
            for st in au.suspects:
                _log(f"THRESHOLD SUSPECT gate {st.n:02d} {st.name}: refused "
                     f"{st.refused_while_measured_passed} structures gate 08 approved")
            journal.append("threshold_audit", {
                "considered": au.considered,
                "suspects": [{"gate": st.n, "name": st.name,
                              "refused_over_measurement": st.refused_while_measured_passed,
                              "best_score_discarded": round(st.best_score_refused, 5),
                              "examples": st.examples} for st in au.suspects]})
        else:
            _log(f"threshold audit clean over {au.considered} structures")
    except Exception as e:
        _log(f"threshold audit skipped ({e})")
    journal.append("agent_start", {"symbols": symbols, "dry_run": dry_run,
                                   "windows": list(ENTRY_WINDOWS_MIN_AFTER_OPEN)})

    while True:
        if Path("STOP").exists():
            _log("STOP file found; exiting.")
            journal.append("agent_stop", {"reason": "STOP file"})
            return
        try:
            state.cycles += 1
            clock = acct.get_clock()

            if not clock["is_open"]:
                if state.cycles % 10 == 1:
                    _log(f"market closed; next open {clock['next_open']}")
                # Idle hours are free; being unmeasured is not. Study a past
                # session and be scored on it, which sharpens the calibration
                # that sets tomorrow's position size at no risk to the account.
                try:
                    from saadhak.witness.state import publish
                    publish()
                except Exception:
                    pass
                try:
                    from saadhak.practitioner.study import study_round
                    r = study_round()
                    if r.scored:
                        _log(f"study: {r.summary}")
                except Exception as e:
                    _log(f"study skipped ({e})")
                time.sleep(min(interval * 5, 300))
                continue

            # 1. exits always run first, even when halted
            monitor_once(dry_run=dry_run, verbose=True)

            # 2. the witness: reconcile against the CLI, resolve due forecasts.
            #    A mismatch stops new entries but never blocks an exit.
            if state.cycles % 5 == 1:
                try:
                    from saadhak.witness.state import publish
                    publish()
                except Exception as e:
                    _log(f"state publish failed ({e})")
                rec = reconcile()
                if not rec.ok:
                    _log(f"RECONCILIATION {rec.summary}")
                cal = calibration_now()
                if cal.n:
                    _log(f"calibration: {cal.verdict}")

            # 3. entries only when not halted and inside a window
            if not check_halts(state):
                mso = acct.minutes_since_open()
                w = due_window(mso)
                if w is not None:
                    # The universe is measured at each window, not assumed once.
                    if pinned is None:
                        try:
                            chosen = tradeable_symbols(universe, top=top, shortlist=14)
                            if chosen:
                                _log(f"screen chose {', '.join(chosen)}")
                                symbols = chosen
                            else:
                                _log("screen found nothing tradeable this window")
                                symbols = []
                        except Exception as e:
                            _log(f"screen failed ({e}); falling back to {s.symbols}")
                            symbols = s.symbols
                    held = {st.underlying for st in open_structures()}
                    for sym in symbols:
                        if sym in held:
                            continue          # gate 5 would refuse anyway
                        try_entry(sym, w, state, dry_run=dry_run)

        except Exception as e:
            _log(f"cycle error: {e}")
            journal.append("agent_error", {"error": str(e)})
        time.sleep(interval)
