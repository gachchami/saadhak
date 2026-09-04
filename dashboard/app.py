"""Saadhak. What the agent considered, what it refused, and why.

Reads only files committed to this repository: the append-only journal and one
published state snapshot. It holds no credentials and can place no orders.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import data as D  # noqa: E402
from components import (  # noqa: E402
    CAL_LEAD, MODEL_LEAD, RECORD_LEAD, STOPS_LEAD,
    bar, capability_section, decision_log, foot, hero, loop_card, md,
    outcome_card, record_section, roster, section, stats, stop_ledger,
    tally_card, wall_card, worksheet,
)
from style import CSS  # noqa: E402

ICON = Path(__file__).resolve().parent / "favicon.png"
st.set_page_config(page_title="Saadhak", layout="wide",
                   initial_sidebar_state="collapsed",
                   **({"page_icon": str(ICON)} if ICON.exists() else {}))
md(CSS)   # a blank line inside <style> would end the raw-HTML block

S = D.snapshot()

md(bar(S))
md('<div class="grid37" style="align-items:end">', hero(S), tally_card(S), '</div>')
md(stats(S))

md(section("Every candidate, every check",
           "One line per trade, running until something stops it"))
md(wall_card(S))

md(section("What stopped them", "Five checks have ever had to refuse anything", STOPS_LEAD))
md(stop_ledger(S), roster(S))
md(f'<p class="note" style="margin-top:22px;max-width:80ch">'
   f'Counted by the check that stopped each trade. Counting every failed check instead gives '
   f'{S["every_failure"]} across {S["refused"]} refusals, because one candidate can fail several. '
   f'Two of these checks were rewritten while the agent was running, and each entry names the '
   f'test that actually ran.</p>')

md(section("How it earns its size", "Its own accuracy decides what it may risk", CAL_LEAD))
md(loop_card(S))
md('<div class="grid2" style="margin-top:20px">', worksheet(S), outcome_card(S), '</div>')

md(section("A second opinion that cannot trade",
           "The model may object, but it has no way to place an order", MODEL_LEAD))
md(capability_section(S))

md(section("The record", "Every decision, including the ones it declined", RECORD_LEAD))
md(decision_log(S))
md(record_section(S))

md(foot(S))
