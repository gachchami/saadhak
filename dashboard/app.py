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
import graphics as G  # noqa: E402
from components import (  # noqa: E402
    CAL_LEAD, HERO_CAPTION, MODEL_LEAD, RECORD_LEAD, STOPS_LEAD,
    cal_verdict, capability_panel, decision_log, footer, legend, md, outcome_strip,
    plate, readouts, record_panel, roster, stop_ledger, verdict, worksheet,
)
from style import CSS  # noqa: E402

ICON = Path(__file__).resolve().parent / "favicon.png"
st.set_page_config(page_title="Saadhak", layout="wide",
                   initial_sidebar_state="collapsed",
                   **({"page_icon": str(ICON)} if ICON.exists() else {}))
md(CSS)   # a blank line inside <style> would end the raw-HTML block

S = D.snapshot()


def rule(label: str) -> str:
    return f'<div class="lead-rule"><span class="eyebrow">{label}</span><i></i></div>'


md(plate(S))
md(verdict(S))

md('<div class="sd-wrap">', rule("Every candidate, every check"),
   '<div class="only-wide">', G.wall_wide(S), '</div>',
   '<div class="only-narrow">', G.wall_narrow(S), '</div>',
   legend(),
   '<p class="prose" style="margin-top:18px">', HERO_CAPTION, '</p>',
   '</div>')

md(readouts(S))

md(rule("What stopped them"), '<p class="lead">', STOPS_LEAD, '</p>',
   stop_ledger(S), roster(S),
   '<p class="note" style="margin-top:20px;max-width:78ch">',
   f'Counted by the check that stopped each trade. Counting every failed check instead gives '
   f'{S["every_failure"]} across {S["refused"]} refusals, because one candidate can fail '
   f'several. Two of these checks were rewritten while the agent was running, and each entry '
   f'names the test that actually ran.', '</p>')

md(rule("How it earns the size it may risk"), '<p class="lead">', CAL_LEAD, '</p>')
md('<div class="sd-wrap">', G.loop_wide(S), '</div>')
md('<div class="duo" style="margin-top:34px"><div>', worksheet(S), '</div>',
   '<div><p class="prose">', cal_verdict(S), '</p>', outcome_strip(S), '</div></div>')

md(rule("A second opinion that cannot trade"), '<p class="lead">', MODEL_LEAD, '</p>',
   capability_panel(S))

md(rule("The record"), '<p class="lead">', RECORD_LEAD, '</p>', decision_log(S))
md(record_panel(S))

md(footer(S))
