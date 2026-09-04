"""Publish what the desk is doing, as a file the dashboard can read.

The dashboard runs on Streamlit Community Cloud from the public repository and
holds no credentials. It reads this file and the journal, both committed, so
anyone can verify the numbers against the Alpaca account id in the submission.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from saadhak.broker import account as acct
from saadhak.engine.sizing import calibration_multiplier
from saadhak.witness import journal
from saadhak.witness.calibration import current as calibration_now
from saadhak.witness.positions import open_structures

STATE = Path("state/latest.json")


def _equity_series(since_iso: str | None) -> list[dict]:
    """Equity through the agent's own lifetime, for the dashboard's curve.

    The paper account was funded before the agent existed, so the broker's
    history opens with a balance that has nothing to do with any decision made
    here. Anchoring on the first journal entry keeps the curve honest: it starts
    where the agent starts.
    """
    try:
        h = acct.portfolio_history(period="1M", timeframe="1D")
        intraday = acct.portfolio_history(period="1W", timeframe="15Min")
    except Exception:
        return []
    points: dict[str, float] = {}
    for src in (h, intraday):
        for t, e in zip(src.get("timestamp") or [], src.get("equity") or [], strict=False):
            if not e:
                continue
            stamp = datetime.fromtimestamp(t, UTC).isoformat(timespec="seconds")
            if since_iso and stamp < since_iso:
                continue
            points[stamp] = round(float(e), 2)
    return [{"t": t, "e": points[t]} for t in sorted(points)]


def build() -> dict:
    a = acct.get_account()
    clock = acct.get_clock()
    cal = calibration_now(resolve=False)
    structures = open_structures()

    everything = journal.read_all()
    started = everything[0]["ts"][:10] if everything else None
    recent = everything[-400:]
    start_equity = next(
        (r["data"]["sizing"]["equity"] for r in everything
         if r["type"] == "gate_result"
         and isinstance(r["data"].get("sizing"), dict)
         and r["data"]["sizing"].get("equity")), None)
    gates = [r for r in everything if r["type"] == "gate_result"]
    refusals = [g for g in gates if g["data"].get("decision") == "refuse"]
    theses = [r for r in everything if r["type"] == "thesis"]
    recs = [r for r in recent if r["type"] == "reconciliation"]

    reasons: dict[str, int] = {}          # counted once, by what stopped the trade
    reasons_all: dict[str, int] = {}      # every check a trade failed
    for g in refusals:
        failed = [x for x in (g["data"].get("gates") or []) if not x.get("ok", True)]
        for x in failed:
            k = f"{x['n']:02d} {x['name']}"
            reasons_all[k] = reasons_all.get(k, 0) + 1
        if failed:
            first = min(failed, key=lambda x: x["n"])
            k = f"{first['n']:02d} {first['name']}"
            reasons[k] = reasons.get(k, 0) + 1

    return {
        "as_of": datetime.now(UTC).isoformat(timespec="seconds"),
        "market_open": bool(clock["is_open"]),
        "account": {
            "id": a.id, "number": a.account_number,
            "equity": a.equity, "cash": a.cash,
            "daily_pl": a.daily_pl, "daily_pl_pct": a.daily_pl_pct,
            "start_equity": start_equity,
            "since_start_pct": (a.equity / start_equity - 1) if start_equity else None,
        },
        "calibration": {
            "brier": cal.brier, "n": cal.n, "mean_p": cal.mean_p,
            "hit_rate": cal.hit_rate, "verdict": cal.verdict,
            "multiplier": calibration_multiplier(cal.brier),
            "risk_per_structure": round(a.equity * 0.015 * calibration_multiplier(cal.brier), 2),
        },
        "open_structures": [{
            "underlying": s.underlying, "expiry": s.expiry.isoformat(),
            "describe": s.describe(), "contracts": s.contracts,
            "entry_credit": s.entry_credit, "cost_to_close": s.cost_to_close,
            "unrealised": s.unrealised, "max_loss": s.max_loss,
            "short_strikes": s.short_strikes,
        } for s in structures],
        "decisions": {
            "total": len(gates), "accepted": len(gates) - len(refusals),
            "refused": len(refusals), "refusal_reasons": reasons,
            "refusal_reasons_all": reasons_all,
        },
        "practitioner": {
            "consulted": sum(1 for t in theses if t["data"].get("consulted")),
            "vetoes": sum(1 for t in theses if t["data"].get("verdict") == "veto"),
            "last": (theses[-1]["data"] if theses else None),
        },
        "reconciliation": (recs[-1]["data"] if recs else None),
        "limiters": __import__("saadhak.practitioner.ratelimit",
                               fromlist=["all_status"]).all_status(),
        "equity_series": _equity_series(started),
        "journal_head": (everything[-1].get("hash") if everything
                         else journal.GENESIS),
    }


def publish() -> dict:
    STATE.parent.mkdir(exist_ok=True)
    s = build()
    STATE.write_text(json.dumps(s, indent=2, default=str) + "\n")
    return s
