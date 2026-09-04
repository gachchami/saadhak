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


def build() -> dict:
    a = acct.get_account()
    clock = acct.get_clock()
    cal = calibration_now(resolve=False)
    structures = open_structures()

    recent = journal.read()[-400:]
    gates = [r for r in recent if r["type"] == "gate_result"]
    refusals = [g for g in gates if g["data"].get("decision") == "refuse"]
    theses = [r for r in recent if r["type"] == "thesis"]
    recs = [r for r in recent if r["type"] == "reconciliation"]

    reasons: dict[str, int] = {}
    for g in refusals:
        for x in g["data"].get("gates", []):
            if not x["ok"]:
                reasons[f"{x['n']:02d} {x['name']}"] = reasons.get(f"{x['n']:02d} {x['name']}", 0) + 1

    return {
        "as_of": datetime.now(UTC).isoformat(timespec="seconds"),
        "market_open": bool(clock["is_open"]),
        "account": {
            "id": a.id, "number": a.account_number,
            "equity": a.equity, "cash": a.cash,
            "daily_pl": a.daily_pl, "daily_pl_pct": a.daily_pl_pct,
            "since_start_pct": a.equity / 100_000 - 1,
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
        },
        "practitioner": {
            "consulted": sum(1 for t in theses if t["data"].get("consulted")),
            "vetoes": sum(1 for t in theses if t["data"].get("verdict") == "veto"),
            "last": (theses[-1]["data"] if theses else None),
        },
        "reconciliation": (recs[-1]["data"] if recs else None),
        "limiters": __import__("saadhak.practitioner.ratelimit",
                               fromlist=["all_status"]).all_status(),
        "journal_head": journal.head(),
    }


def publish() -> dict:
    STATE.parent.mkdir(exist_ok=True)
    s = build()
    STATE.write_text(json.dumps(s, indent=2, default=str) + "\n")
    return s
