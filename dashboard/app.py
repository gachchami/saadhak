"""Saadhak dashboard. Reads the committed state file and journal; holds no keys."""
from __future__ import annotations

import glob
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "latest.json"

st.set_page_config(page_title="Saadhak", page_icon="साध", layout="wide")

CSS = """
<style>
  .stApp { background: #0f1216; }
  h1, h2, h3 { color: #e8eaed; }
  .metric-note { color: #9aa4b2; font-size: 0.8rem; }
  .verdict { font-size: 1.05rem; padding: .6rem .9rem; border-radius: 8px;
             background: #171c22; border-left: 3px solid #d4a24c; color:#e8eaed; }
  .refuse { color: #e2798b; } .accept { color: #5dbf90; }
  code { color: #8bd5ca; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(ttl=30)
def load_state() -> dict | None:
    if not STATE.exists():
        return None
    return json.loads(STATE.read_text())


@st.cache_data(ttl=30)
def load_journal(limit: int = 3000) -> list[dict]:
    out = []
    for p in sorted(glob.glob(str(ROOT / "journal" / "*.jsonl"))):
        for line in Path(p).read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out[-limit:]


s = load_state()
records = load_journal()

st.title("साधक · Saadhak")
st.caption("An autonomous options agent that sizes itself by its own calibration. "
           "Alpaca paper trading. The model proposes, the discipline decides, "
           "a witness keeps score.")

if not s:
    st.warning("No state published yet. Run `uv run saadhak publish`.")
    st.stop()

acct = s["account"]
cal = s["calibration"]
dec = s["decisions"]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Equity", f"${acct['equity']:,.2f}", f"{acct['daily_pl']:+,.2f} today")
c2.metric("Since start", f"{acct['since_start_pct']:+.2%}")
c3.metric("Open structures", len(s["open_structures"]))
c4.metric("Decisions", dec["total"], f"{dec['refused']} refused")
c5.metric("Risk allowed", f"${cal['risk_per_structure']:,.0f}",
          f"{cal['multiplier']:.2f}x earned")

st.markdown("### Calibration — how the agent earns its size")
st.markdown(f"<div class='verdict'>{cal['verdict']}</div>", unsafe_allow_html=True)
st.caption(
    "Every review states a probability. Those are scored against what actually "
    "happened with a Brier score, and the score sets how much the desk may risk. "
    "Saying 90% and being right half the time is punished; the model has to earn "
    "size by knowing what it knows. The band is set by the engine, not the model, "
    "so a wider guess cannot buy a better score."
)

resolved = [r["data"] for r in records if r["type"] == "forecast_resolved"]
if resolved:
    rows = [{"symbol": r["symbol"], "day": r["expiry"],
             "band": f"{r['lo']:g}–{r['hi']:g}", "said": f"{r['p']:.0%}",
             "close": f"{r['close']:.2f}",
             "right": "yes" if r["inside"] else "no",
             "penalty": round(r.get("brier_contribution", 0), 3)}
            for r in resolved[-15:]]
    st.dataframe(rows, use_container_width=True, hide_index=True)

left, right = st.columns([3, 2])

with left:
    st.markdown("### Open positions")
    if s["open_structures"]:
        for o in s["open_structures"]:
            st.markdown(f"**{o['describe']}**")
            a, b, c, d = st.columns(4)
            a.metric("Credit", f"${o['entry_credit']:.2f}")
            b.metric("Cost to close", f"${o['cost_to_close']:.2f}")
            c.metric("Unrealised", f"${o['unrealised']:+,.0f}")
            d.metric("Max loss", f"${o['max_loss']:,.0f}")
    else:
        st.info("Flat.")

    st.markdown("### Decisions, including refusals")
    st.caption("A refusal with a stated reason is the point. The agent explains "
               "every trade it declined, not only the ones it took.")
    gates = [r for r in records if r["type"] == "gate_result"][-12:]
    for g in reversed(gates):
        d = g["data"]
        ok = d.get("decision") == "accept"
        head = "accept" if ok else "refuse"
        cls = "accept" if ok else "refuse"
        with st.expander(f"{d.get('structure', '?')} — {head}", expanded=False):
            bad = [x for x in d.get("gates", []) if not x["ok"]]
            if bad:
                for x in bad:
                    st.markdown(f"<span class='refuse'>gate {x['n']:02d} "
                                f"{x['name']}</span>: {x['reason']}",
                                unsafe_allow_html=True)
            else:
                st.markdown("<span class='accept'>all seventeen gates passed"
                            "</span>", unsafe_allow_html=True)
            if d.get("provenance"):
                st.caption(f"data: {d['provenance'].get('note', '')}")

with right:
    st.markdown("### Why trades were refused")
    if dec["refusal_reasons"]:
        st.bar_chart(dec["refusal_reasons"], horizontal=True)
    else:
        st.caption("No refusals recorded yet.")

    st.markdown("### The practitioner")
    p = s["practitioner"]
    st.caption(f"consulted {p['consulted']} times · {p['vetoes']} vetoes")
    if p.get("last"):
        last = p["last"]
        if not last.get("consulted"):
            st.markdown(f"**unavailable** — {last.get('error', 'no reply')}")
            st.caption("The engine traded on the gates alone. A failed review is "
                       "recorded as a failure, never as agreement.")
        else:
            ps, ew = last.get("p_success"), last.get("engine_win_prob")
            st.markdown(f"**{last.get('verdict', '?')}** · model "
                        f"{ps:.0%}" .format(ps=ps) if isinstance(ps, float) else
                        f"**{last.get('verdict', '?')}**")
            if isinstance(ps, float) and isinstance(ew, float):
                st.caption(f"model {ps:.0%} vs engine {ew:.0%}")
            st.write(last.get("thesis", ""))
            st.caption(f"via MCP: {', '.join(last.get('mcp_tools_called', []))} · "
                       f"model {last.get('model', '')}")
    st.caption("The MCP server is started without the trading toolset, so the "
               "model cannot place an order. It may veto; it cannot trade.")

    st.markdown("### Witness")
    rec = s.get("reconciliation")
    if rec:
        st.markdown("Broker state checked through the **Alpaca CLI** against the "
                    "engine's own REST view.")
        st.write("agree" if rec.get("ok") else f"MISMATCH: {rec.get('diffs')}")
    lims = s.get("limiters") or {}
    if lims:
        st.markdown("### Model routing")
        for m, l in sorted(lims.items()):
            if m == "default":
                continue
            st.caption(f"**{m}** — {l['rate_per_min']}/min · {l['state']} · "
                       f"{l['allowed']} sent, {l['throttled_by_provider']} throttled")
        st.caption("Each model has its own learned rate, because a saturated "
                   "upstream belongs to the model rather than to the account. "
                   "When one is throttled the next answers.")
    st.caption(f"journal head `{s['journal_head'][:16]}…`")

st.divider()
st.caption(
    f"Alpaca paper account {acct['number']} · id {acct['id']} · "
    f"state as of {s['as_of']} · "
    "free data tier: IEX stock quotes, indicative option quotes, no OPRA."
)
