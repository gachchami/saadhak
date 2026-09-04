"""Everything the page knows, derived once.

Two sources, with a strict division of labour. The journal is the only source of
decision counts, because it is the record that can be checked; the published
state file supplies only what the dashboard cannot compute for itself, which is
the live account, the calibration figures and the broker reconciliation.

Standard library and Streamlit only. This runs on Streamlit Community Cloud from
the public repository with no credentials of any kind.
"""
from __future__ import annotations

import glob
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "latest.json"
JOURNAL = ROOT / "journal"
GENESIS = "0" * 64
START_EQUITY_FALLBACK = 100_000.0

# ---------------------------------------------------------------- check names

# Keyed on (number, name) because two checks were rewritten while the agent was
# running. A record that failed the old test must still say what the old test
# actually did, so history is not retold with today's vocabulary.
RAIL = {
    1: "Market hours", 2: "Approved symbol", 3: "Risk is capped",
    4: "Worst case fits", 5: "Book has room", 6: "Loss halts clear",
    7: "Both sides liquid", 8: "Premium vs odds", 9: "Strike data",
    10: "Time to expiry", 11: "No event due", 12: "At least one lot",
    13: "One order, one id", 14: "Limit orders only", 15: "Exit plan attached",
    16: "Broker agrees", 17: "Kill switch clear", 18: "No losing streak",
    19: "Not a repeat bet",
}

STOP_NAME = {
    (1, "market_hours"): "Outside trading hours",
    (2, "whitelist"): "Symbol is not on the approved list",
    (3, "defined_risk"): "Loss was not capped",
    (4, "max_loss"): "Worst case too large for the account",
    (5, "portfolio_caps"): "No room left in the book",
    (6, "loss_halts"): "A loss halt was in force",
    (7, "liquidity"): "No tradeable market on one leg",
    (8, "credit_floor"): "Premium too small for the risk",
    (8, "expectancy"): "Premium did not beat the breakeven odds",
    (9, "short_delta"): "Strikes outside the intended band",
    (9, "delta_data"): "Strike data was unusable",
    (10, "dte"): "Wrong distance from expiry",
    (11, "event_guard"): "A scheduled event fell inside the trade",
    (12, "sizeable"): "Too small to be worth placing",
    (13, "idempotent_id"): "Order identity was not unique",
    (14, "limit_only"): "Would not have been a limit order",
    (15, "exit_rules"): "No exit plan attached",
    (16, "reconciled"): "Broker and engine disagreed",
    (17, "kill_switch"): "The kill switch was set",
    (18, "regime"): "Too many losses in a row",
    (19, "correlation"): "Too close to a bet already on",
}

WHY = {
    (1, "market_hours"): "The market was closed, or too near the bell to open a position.",
    (2, "whitelist"): "The search looks at a wider market than this desk is allowed to trade.",
    (7, "liquidity"): "There was no price on the side the order would have had to cross.",
    (8, "credit_floor"): "The credit taken in did not cover what the exit rules would need.",
    (8, "expectancy"): "The premium on offer did not pay for the odds of the trade working.",
    (9, "short_delta"): "The short strikes sat further out than the rule then allowed.",
    (9, "delta_data"): "The strike data was not good enough to judge the trade on.",
}

TOOL_NAMES = {
    "get_stock_snapshot": "Stock quotes",
    "get_news": "News headlines",
    "get_option_chain": "Option chains",
    "get_positions": "Open positions",
    "get_stock_bars": "Price history",
}


def check_label(n: int, name: str) -> str:
    """Plain English for a check, never a number and never an identifier."""
    if (n, name) in STOP_NAME:
        return STOP_NAME[(n, name)]
    if n in RAIL:
        return RAIL[n]
    return str(name).replace("_", " ").strip().capitalize() or "Unnamed check"


# ------------------------------------------------------------------- loading


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@st.cache_data(ttl=60)
def load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


@st.cache_data(ttl=60)
def load_journal() -> tuple[list[dict], dict]:
    """Every record, oldest first, plus the result of recomputing the chain.

    Each day is its own file and its own chain, so verification restarts from
    the genesis hash at the top of every file.
    """
    records: list[dict] = []
    total = 0
    broken: str | None = None
    for path in sorted(glob.glob(str(JOURNAL / "*.jsonl"))):
        prev = GENESIS
        try:
            lines = Path(path).read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            total += 1
            if broken is None:
                want = hashlib.sha256(
                    (prev + _canonical(rec.get("data"))).encode()).hexdigest()
                if rec.get("prev_hash") != prev or rec.get("hash") != want:
                    broken = f"entry {rec.get('seq')} in {Path(path).name}"
                prev = rec.get("hash") or prev
            records.append(rec)
    head = records[-1].get("hash", GENESIS) if records else GENESIS
    return records, {"entries": total, "intact": broken is None,
                     "broken_at": broken, "head": head}


# ------------------------------------------------------------------ derived


def _fmt_structure(s: str) -> str:
    """'SPY 2026-09-02 iron_condor 749/754/768/773 x1 @ +0.36' read aloud."""
    parts = str(s or "").split()
    if len(parts) < 6:
        return str(s or "—")
    sym, _expiry, kind, strikes, lots, _at, credit = (parts + [""] * 7)[:7]
    kind = kind.replace("_", " ")
    n = lots.lstrip("x") or "?"
    lot_word = "lot" if n == "1" else "lots"
    try:
        credit_txt = f"credit ${abs(float(credit)):.2f}"
    except ValueError:
        credit_txt = str(credit)
    return f"{sym} · {kind} · {strikes} · {n} {lot_word} · {credit_txt}"


def _first_failure(gates: list[dict]) -> dict | None:
    bad = [g for g in gates if isinstance(g, dict) and not g.get("ok", True)]
    return min(bad, key=lambda g: g.get("n", 99)) if bad else None


def _age(iso: str | None) -> tuple[str, float]:
    if not iso:
        return "unknown", 1e9
    try:
        then = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return "unknown", 1e9
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    hours = (datetime.now(UTC) - then).total_seconds() / 3600
    if hours < 1:
        return f"{max(int(hours * 60), 1)} minutes ago", hours
    if hours < 48:
        n = int(round(hours))
        return f"{n} hour{'s' if n != 1 else ''} ago", hours
    return f"{int(hours / 24)} days ago", hours


@st.cache_data(ttl=60)
def snapshot() -> dict:
    state = load_state()
    records, chain = load_journal()

    account = state.get("account") or {}
    cal = state.get("calibration") or {}

    gate_recs = [r for r in records
                 if r.get("type") == "gate_result" and isinstance(r.get("data"), dict)]

    rows, stop_counts, every_failure = [], {}, 0
    for r in gate_recs:
        d = r["data"]
        gates = [g for g in (d.get("gates") or []) if isinstance(g, dict)]
        fail = _first_failure(gates)
        every_failure += sum(1 for g in gates if not g.get("ok", True))
        key = (fail.get("n"), fail.get("name")) if fail else None
        if key:
            stop_counts[key] = stop_counts.get(key, 0) + 1
        exp = d.get("expectancy") if isinstance(d.get("expectancy"), dict) else {}
        rows.append({
            "ts": r.get("ts", ""),
            "time": str(r.get("ts", ""))[11:16],
            "structure": _fmt_structure(d.get("structure")),
            "stopped": fail is not None,
            "key": key,
            "stopped_by": check_label(*key) if key else None,
            "reason": (fail.get("reason") if fail else _passed_note(exp, len(gates))),
            "checks_run": len(gates),
        })

    refused = sum(1 for x in rows if x["stopped"])
    accepted = len(rows) - refused

    theses = [r.get("data") or {} for r in records if r.get("type") == "thesis"]
    verdicts = [t.get("verdict") for t in theses]
    vetoed = [t for t in theses if t.get("veto_reason")]

    forecasts = [r.get("data") or {} for r in records
                 if r.get("type") == "forecast_resolved"
                 and (r.get("data") or {}).get("task") == "fixed_band"]
    settled = [f for f in forecasts[-40:] if f.get("inside") is not None]

    tools: list[str] = []
    for t in theses:
        for name in (t.get("mcp_tools_called") or []):
            pretty = TOOL_NAMES.get(name, str(name).replace("_", " ").replace("get ", "").capitalize())
            if pretty not in tools:
                tools.append(pretty)

    start_equity = _start_equity(gate_recs)
    equity = _f(account.get("equity"))
    since = (equity / start_equity - 1) if (equity and start_equity) else None

    age_txt, age_hours = _age(state.get("as_of"))
    cap = (equity or 0) * 0.015

    return {
        "as_of": state.get("as_of"), "age": age_txt, "stale": age_hours > 6,
        "market_open": bool(state.get("market_open")),
        "account_number": account.get("number") or "—",
        "equity": equity, "start_equity": start_equity, "since": since,
        "open_structures": state.get("open_structures") or [],
        "rows": rows, "total": len(rows), "refused": refused, "accepted": accepted,
        "stop_counts": stop_counts, "every_failure": every_failure,
        "brier": _f(cal.get("brier")), "mean_p": _f(cal.get("mean_p")),
        "hit_rate": _f(cal.get("hit_rate")), "n_scored": cal.get("n") or 0,
        "multiplier": _f(cal.get("multiplier")), "cap": cap,
        "risk_allowed": _f(cal.get("risk_per_structure")),
        "settled": settled, "inside": sum(1 for f in settled if f.get("inside")),
        "reviews": len(theses),
        "agreed": sum(1 for v in verdicts if v == "agree"),
        "objected": sum(1 for v in verdicts if v == "veto"),
        "silent": sum(1 for v in verdicts if v not in ("agree", "veto")),
        "last_veto": vetoed[-1] if vetoed else None,
        "last_review": theses[-1] if theses else None,
        "tools": tools,
        "chain": chain,
        "reconciliation": state.get("reconciliation") or {},
        "limiters": state.get("limiters") or {},
        "equity_series": state.get("equity_series") or [],
    }


def _passed_note(exp: dict, n_checks: int) -> str:
    if exp:
        try:
            return (f"win {exp['win_prob']:.0%} vs breakeven {exp['breakeven']:.0%}"
                    f" · EV ${exp['ev_per_contract']:+.2f} per contract")
        except (KeyError, TypeError, ValueError):
            pass
    return f"cleared all {n_checks} checks"


def _start_equity(gate_recs: list[dict]) -> float:
    """The first balance the program actually observed, not an assumed round number."""
    for r in gate_recs:
        sizing = (r.get("data") or {}).get("sizing")
        if isinstance(sizing, dict) and sizing.get("equity"):
            try:
                return float(sizing["equity"])
            except (TypeError, ValueError):
                continue
    return START_EQUITY_FALLBACK


def _f(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
