"""Saadhak — the operator's screen.

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
    broker, capability, closed_table, foot, funnel, integrity, kpis, ledger,
    log_table, md, panel, rail, review_counts, roster, sb, stop_table, topbar,
    veto_panel, wall, worksheet, outcomes,
)
from style import CSS  # noqa: E402

ICON = Path(__file__).resolve().parent / "favicon.png"
st.set_page_config(page_title="Saadhak", layout="wide",
                   initial_sidebar_state="expanded",
                   **({"page_icon": str(ICON)} if ICON.exists() else {}))
md(CSS)   # a blank line inside <style> would end the raw-HTML block

S = D.snapshot()

sb(rail(S))
md(topbar(S))
md(kpis(S))

md('<div class="row">',
   panel("The account, to the cent", ledger(S),
         meta="funding, realised profit and fees", cls="c4"),
   panel("Equity since it started", f'<div class="sd-wrap">{G.equity_spark(S, 720, 190)}</div>',
         meta="15-minute marks", cls="c8"),
   '</div>')

md('<div class="row" id="gauntlet">',
   panel("Every candidate against every check", wall(S),
         meta=f'{S["total"]} candidates · {S["refused"]} stopped · {S["accepted"]} cleared',
         cls="c12"),
   '</div>')

md('<div class="row" id="refusals">',
   panel("What stopped them", stop_table(S),
         meta=f'{S["every_failure"]} failures across {S["refused"]} refusals',
         cls="c7", flush=True),
   panel("All nineteen checks", roster(S), meta="lit ones have refused something", cls="c5"),
   '</div>')

md('<div class="row" id="positions">',
   panel("From candidate to filled order", funnel(S), meta="where the 48 went", cls="c5"),
   panel("Closed positions", closed_table(S),
         meta=f'{len(S["closed"])} closed · all stopped out', cls="c7", flush=True),
   '</div>')

md('<div class="row" id="calibration">',
   panel("Its own accuracy sets its size",
         f'<div class="sd-wrap">{G.loop_wide(S)}</div>', cls="c12"),
   '</div>')

md('<div class="row">',
   panel("How the next size is worked out", worksheet(S), cls="c4"),
   panel("Forecasts settled against the close", outcomes(S),
         meta=f'{S["inside"]} of {len(S["settled"])} inside', cls="c8"),
   '</div>')

md('<div class="row" id="review">',
   panel("The model cannot place an order", capability(S), cls="c5"),
   panel("What the reviews did", review_counts(S), meta=f'{S["reviews"]} reviews', cls="c3"),
   panel("The last time it objected, in its own words", veto_panel(S), cls="c4"),
   '</div>')

md('<div class="row" id="journal">',
   panel("Decision journal", log_table(S),
         meta=f'most recent 18 of {S["total"]} · every one is committed', cls="c12", flush=True),
   '</div>')

md('<div class="row">',
   panel("The log checks out", integrity(S),
         meta=f'{S["chain"]["entries"]:,} entries', cls="c6"),
   panel("The broker agrees", broker(S), meta="checked twice, two ways", cls="c6"),
   '</div>')

md(foot(S))
