"""The monitor loop. Exits are enforced here, by rules attached at entry."""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from saadhak.broker import account as acct
from saadhak.broker.client import AlpacaError, trading
from saadhak.broker.orders import cancel, open_orders
from saadhak.broker.data import latest_price
from saadhak.config import settings
from saadhak.witness import journal
from saadhak.witness.positions import OpenStructure, open_structures


def clock_is_open() -> bool:
    try:
        return bool(acct.get_clock()["is_open"])
    except Exception:
        return False


def exit_check(st: OpenStructure, spot: float, minutes_to_close: float | None) -> tuple[bool, str, str]:
    s = settings()
    entry, cost = st.entry_credit, st.cost_to_close
    tp = round(entry * (1 - s.take_profit_pct), 4)
    sl = round(entry * s.stop_loss_multiple, 4)

    if cost <= tp:
        return True, "tp_50pct", f"cost ${cost:.2f} <= target ${tp:.2f} (50% of ${entry:.2f})"
    if cost >= sl:
        return True, "sl_2x", f"cost ${cost:.2f} >= stop ${sl:.2f} (2x credit)"
    if minutes_to_close is not None:
        expiring = st.expiry <= datetime.now(UTC).date()
        if expiring and minutes_to_close <= 15:
            # The time stop exists to avoid assignment and pin risk, NOT to
            # close positions that are about to expire worthless. Closing a
            # safely out-of-the-money credit spread pays the spread to give up
            # the whole credit. Only exit if a short leg is actually threatened.
            buffer = max(st.width, spot * s.expiry_danger_pct)
            threatened = st.threatened_shorts(spot, buffer)
            if threatened:
                return True, "time_stop", (f"{minutes_to_close:.0f}m to close, "
                                           f"assignment risk: {', '.join(threatened)}")
            return False, "expire_worthless", (
                f"{minutes_to_close:.0f}m to close, all shorts clear of spot "
                f"{spot:.2f} by more than {buffer:.2f}; holding to expiry keeps "
                f"the full ${entry:.2f} credit")
        if minutes_to_close <= 30:
            for k in st.short_strikes:
                if abs(k - spot) / spot <= s.proximity_pct:
                    return True, "proximity", f"short {k:g} within {s.proximity_pct:.1%} of {spot:.2f}"
    return False, "hold", f"cost ${cost:.2f} between ${tp:.2f} and ${sl:.2f}"


def close(st: OpenStructure, *, dry_run: bool, reason: str) -> dict:
    """Close at the mid, as a signed debit; never a market order."""
    body = {
        "order_class": "mleg", "qty": str(st.contracts), "type": "limit",
        "time_in_force": "day",
        "limit_price": f"{abs(st.cost_to_close):.2f}",   # paying to close = positive
        "legs": st.closing_legs(),
    }
    if dry_run:
        journal.append("exit", {"structure": st.describe(), "rule": reason,
                                "dry_run": True, "body": body, "pl": st.unrealised})
        return {"status": "dry_run", "body": body}
    try:
        resp = trading("/orders", method="POST", json=body)
        journal.append("exit", {"structure": st.describe(), "rule": reason, "dry_run": False,
                                "body": body, "order_id": resp.get("id"),
                                "pl": st.unrealised})
        return resp
    except AlpacaError as e:
        journal.append("exit_failed", {"structure": st.describe(), "rule": reason,
                                       "body": body, "error": str(e)})
        return {"status": "error", "error": str(e)}


def sweep_stale_orders(*, max_age_min: float = 5.0, dry_run: bool = False,
                       verbose: bool = True) -> list[str]:
    """Cancel entry orders that never filled.

    An unfilled limit order is not harmless. It can fill hours later, at a price
    the decision was not made at, into a position nothing is watching yet, and it
    is invisible to the portfolio caps, which count positions rather than intent.
    One sat open for ninety minutes today because the limit walk was written and
    never called.
    """
    killed = []
    now = datetime.now(UTC)
    for o in open_orders():
        try:
            age = (now - datetime.fromisoformat(
                o["submitted_at"].replace("Z", "+00:00"))).total_seconds() / 60.0
        except Exception:
            continue
        if age < max_age_min:
            continue
        if verbose:
            print(f"    stale order {o['id'][:8]} unfilled for {age:.0f}m at "
                  f"{o.get('limit_price')} — cancelling", flush=True)
        journal.append("order_cancelled", {
            "order_id": o["id"], "age_min": round(age, 1),
            "limit_price": o.get("limit_price"), "reason": "unfilled at the mid",
            "dry_run": dry_run})
        if not dry_run:
            try:
                cancel(o["id"])
            except AlpacaError as e:
                print(f"    cancel failed: {e}", flush=True)
                continue
        killed.append(o["id"])
    return killed


def monitor_once(*, dry_run: bool, verbose: bool = True) -> list[dict]:
    out = []
    if clock_is_open():
        sweep_stale_orders(dry_run=dry_run, verbose=verbose)
    clock = acct.get_clock()
    mtc = acct.minutes_to_close()
    for st in open_structures():
        spot = latest_price(st.underlying)
        should, rule, detail = exit_check(st, spot, mtc)
        line = {"structure": st.describe(), "spot": spot, "entry_credit": st.entry_credit,
                "cost_to_close": st.cost_to_close, "unrealised": st.unrealised,
                "rule": rule, "detail": detail, "exiting": should}
        if verbose:
            ts = datetime.now(UTC).strftime("%H:%M:%S")
            print(f"[{ts}Z] {st.describe()}  spot {spot:.2f}  "
                  f"cost {st.cost_to_close:+.2f} vs credit {st.entry_credit:+.2f}  "
                  f"P/L ${st.unrealised:+,.0f}  -> {rule}: {detail}", flush=True)
        if should and clock["is_open"]:
            line["result"] = close(st, dry_run=dry_run, reason=rule)
            if verbose:
                print(f"    EXIT {rule}: {line['result'].get('status', 'submitted')}", flush=True)
        out.append(line)
    return out


def run_monitor(*, dry_run: bool, interval: int = 60, verbose: bool = True) -> None:
    print(f"monitor started (interval {interval}s, dry_run={dry_run}); "
          f"touch STOP to halt", flush=True)
    while True:
        if Path("STOP").exists():
            journal.append("halt", {"reason": "STOP file present"})
            print("STOP file found; monitor exiting.", flush=True)
            return
        try:
            rows = monitor_once(dry_run=dry_run, verbose=verbose)
            if not rows and verbose:
                print(f"[{datetime.now(UTC):%H:%M:%S}Z] no open structures", flush=True)
        except Exception as e:                     # never let the loop die
            print(f"monitor error: {e}", flush=True)
            journal.append("monitor_error", {"error": str(e)})
        time.sleep(interval)
