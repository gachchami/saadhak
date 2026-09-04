"""Append-only, hash-chained journal. The repo is the audit trail."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JOURNAL_DIR = Path("journal")
GENESIS = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def path_for(day: str | None = None) -> Path:
    day = day or datetime.now(UTC).date().isoformat()
    return JOURNAL_DIR / f"{day}.jsonl"


def head(day: str | None = None) -> str:
    p = path_for(day)
    if not p.exists():
        return GENESIS
    last = None
    for line in p.read_text().splitlines():
        if line.strip():
            last = line
    return json.loads(last)["hash"] if last else GENESIS


def append(kind: str, data: dict) -> dict:
    JOURNAL_DIR.mkdir(exist_ok=True)
    p = path_for()
    prev = head()
    seq = sum(1 for _ in p.read_text().splitlines() if _.strip()) if p.exists() else 0
    rec = {"seq": seq, "ts": datetime.now(UTC).isoformat(), "type": kind,
           "prev_hash": prev, "data": data}
    rec["hash"] = hashlib.sha256((prev + _canonical(data)).encode()).hexdigest()
    with p.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    return rec


def read(day: str | None = None) -> list[dict]:
    p = path_for(day)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def verify(day: str | None = None) -> tuple[bool, str]:
    prev = GENESIS
    for rec in read(day):
        want = hashlib.sha256((prev + _canonical(rec["data"])).encode()).hexdigest()
        if rec["prev_hash"] != prev:
            return False, f"seq {rec['seq']}: prev_hash mismatch"
        if rec["hash"] != want:
            return False, f"seq {rec['seq']}: hash mismatch (record altered)"
        prev = rec["hash"]
    return True, f"chain intact ({len(read(day))} records)"
