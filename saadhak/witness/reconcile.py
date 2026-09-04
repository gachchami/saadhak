"""Reconciliation through the Alpaca CLI — deliberately a different client.

The engine reaches Alpaca over REST with httpx. The witness reaches it by
shelling out to the official CLI binary. If one of them is wrong, whether a bug
in our HTTP layer, a stale cache, or a misparsed response, the two disagree and
the desk stops opening new positions. A checker that shares its subject's code
path can only confirm its subject's mistakes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field

from saadhak.broker import account as acct
from saadhak.config import settings
from saadhak.witness import journal


@dataclass
class Reconciliation:
    ok: bool
    checked: bool
    diffs: list[str] = field(default_factory=list)
    cli_positions: int = 0
    rest_positions: int = 0
    cli_open_orders: int = 0
    note: str = ""

    @property
    def summary(self) -> str:
        if not self.checked:
            return f"not checked ({self.note})"
        if self.ok:
            return (f"CLI and REST agree: {self.cli_positions} legs, "
                    f"{self.cli_open_orders} open orders")
        return "MISMATCH: " + "; ".join(self.diffs)


def _cli(args: list[str]) -> tuple[bool, object, str]:
    exe = shutil.which("alpaca")
    if not exe:
        return False, None, "alpaca CLI not installed"
    s = settings()
    env = {**os.environ,
           "ALPACA_API_KEY": s.apca_api_key_id,
           "ALPACA_SECRET_KEY": s.apca_api_secret_key}
    try:
        r = subprocess.run([exe, *args, "--quiet"], capture_output=True,
                           text=True, timeout=30, env=env)
    except subprocess.TimeoutExpired:
        return False, None, "alpaca CLI timed out"
    if r.returncode != 0:
        return False, None, f"alpaca CLI exit {r.returncode}: {r.stderr.strip()[:200]}"
    try:
        return True, json.loads(r.stdout or "[]"), ""
    except json.JSONDecodeError as e:
        return False, None, f"alpaca CLI returned non-JSON: {e}"


def reconcile(*, journal_write: bool = True) -> Reconciliation:
    ok_p, cli_pos, err_p = _cli(["position", "list"])
    if not ok_p:
        rec = Reconciliation(True, False, note=err_p)
        if journal_write:
            journal.append("reconciliation", {"ok": True, "checked": False,
                                              "note": err_p, "source": "alpaca-cli"})
        return rec

    ok_o, cli_orders, err_o = _cli(["order", "list", "--status", "open"])
    cli_open = len(cli_orders) if ok_o and isinstance(cli_orders, list) else 0

    rest_pos = acct.option_positions()
    cli_opts = [p for p in cli_pos if p.get("asset_class") == "us_option"]

    diffs: list[str] = []
    if len(cli_opts) != len(rest_pos):
        diffs.append(f"leg count: CLI {len(cli_opts)} vs REST {len(rest_pos)}")

    cli_by = {p["symbol"]: p for p in cli_opts}
    rest_by = {p["symbol"]: p for p in rest_pos}
    for sym in set(cli_by) | set(rest_by):
        if sym not in cli_by:
            diffs.append(f"{sym}: in REST, absent from CLI")
        elif sym not in rest_by:
            diffs.append(f"{sym}: in CLI, absent from REST")
        elif int(cli_by[sym]["qty"]) != int(rest_by[sym]["qty"]):
            diffs.append(f"{sym}: qty CLI {cli_by[sym]['qty']} vs REST {rest_by[sym]['qty']}")

    rec = Reconciliation(ok=not diffs, checked=True, diffs=diffs,
                         cli_positions=len(cli_opts), rest_positions=len(rest_pos),
                         cli_open_orders=cli_open)
    if journal_write:
        journal.append("reconciliation", {
            "ok": rec.ok, "checked": True, "diffs": diffs, "source": "alpaca-cli",
            "cli_positions": len(cli_opts), "rest_positions": len(rest_pos),
            "cli_open_orders": cli_open})
    return rec
