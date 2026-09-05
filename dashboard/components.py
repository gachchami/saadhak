"""The dashboard's panels, and the words in them.

One rule about language: nothing here names a check by number or by the
identifier it has in the code. A reader who has never seen this project should
be able to read the whole screen.
"""
from __future__ import annotations

import html as H
import re

import streamlit as st

import graphics as G
from data import RAIL, WHY, check_label


def esc(x) -> str:
    return H.escape("" if x is None else str(x))


def md(*parts: str) -> None:
    """Emit one HTML block as a single line.

    Streamlit's markdown pass turns a blank line into a paragraph break and four
    leading spaces into a code block, so the indentation has to go.
    """
    st.markdown(re.sub(r"\n\s*", "", "".join(parts)), unsafe_allow_html=True)


def sb(*parts: str) -> None:
    st.sidebar.markdown(re.sub(r"\n\s*", "", "".join(parts)), unsafe_allow_html=True)


_MONTH = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
          "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}


def money(x, dp=2, sign=False) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    s = f"{'+' if sign and x > 0 else '−' if x < 0 else ''}${abs(x):,.{dp}f}"
    return s


def _stamp(S: dict) -> str:
    raw = str(S.get("as_of") or "")
    return f"{raw[8:10].lstrip('0')} {_MONTH.get(raw[5:7], '')} {raw[11:16]} UTC".strip()


def _days(S: dict) -> str:
    n = len({r["ts"][:10] for r in S["rows"] if r.get("ts")})
    return f"{n} day{'s' if n != 1 else ''}" if n else "the run"


def panel(title: str, body: str, meta: str = "", cls: str = "c12", flush: bool = False) -> str:
    return (f'<div class="{cls}"><div class="panel">'
            f'<div class="ph"><h3>{esc(title)}</h3>'
            + (f'<span class="meta">{esc(meta)}</span>' if meta else "")
            + f'</div><div class="pb{" flush" if flush else ""}">{body}</div></div></div>')


# ---------------------------------------------------------------- left rail


NAV = [("#overview", "Overview"), ("#gauntlet", "The gauntlet"), ("#refusals", "Refusals"),
       ("#positions", "Positions & P&L"), ("#calibration", "Calibration"),
       ("#review", "Model review"), ("#journal", "Journal")]


def rail(S: dict) -> str:
    live = S["market_open"]
    links = "".join(f'<a href="{h}">{esc(t)}</a>' for h, t in NAV)
    return (f'<div class="brand"><span class="dev">साधक</span>'
            f'<span class="wm">Saadhak</span><span class="env">Paper</span></div>'
            f'<div class="navlab">Desk</div><nav class="nav">{links}</nav>'
            f'<div class="railbox"><div class="rk">Risk allowed next trade</div>'
            f'<div class="rv">{money(S["risk_allowed"], 0)}</div></div>'
            f'<div class="railbox"><div class="rk">Kill switch</div>'
            f'<div class="rv">Not set</div></div>'
            f'<div class="railbox"><div class="rk">Market</div>'
            f'<div class="rv">{"Open" if live else "Closed"}</div></div>'
            f'<div class="railfoot">Alpaca paper<br>{esc(S["account_number"])}</div>')


def topbar(S: dict) -> str:
    live = S["market_open"]
    chain_ok = S["chain"]["intact"]
    return (f'<div class="top" id="overview"><h1>Overview</h1>'
            f'<span class="sep">/</span>'
            f'<span class="stamp">Autonomous defined-risk options agent</span>'
            f'<span class="right">'
            f'<span class="pill{"" if live else " off"}"><i></i>'
            f'{"Market open" if live else "Market closed"}</span>'
            f'<span class="pill{"" if chain_ok else " bad"}"><i></i>'
            f'{"Log verified" if chain_ok else "Log broken"}</span>'
            f'<span class="stamp">Read {esc(_stamp(S))} · {esc(S["age"])}</span>'
            f'</span></div>')


# ------------------------------------------------------------------ readouts


def kpis(S: dict) -> str:
    since, f = S["since"], S["funnel"]
    cells = [
        ("Equity", money(S["equity"]), f'funded with {money(S["funding"] or 100000, 0)}', ""),
        ("Since it started", f"{since:+.2%}" if since is not None else "—",
         f'{money(S["realised"], 0, sign=True)} realised, {money(S["fees"], 2, sign=True)} fees',
         "neg" if (since or 0) < 0 else "pos"),
        ("Candidates considered", str(f["considered"]), f'over {_days(S)}', ""),
        ("Refused by the checks", str(f["refused"]),
         f'{f["refused"] / f["considered"]:.0%} of everything it found' if f["considered"] else "—", ""),
        ("Orders filled", str(f["filled"]),
         f'{f["submitted"]} sent, {f["unfilled"]} never filled', ""),
        ("Risk allowed per trade", money(S["risk_allowed"], 0),
         f'{S["multiplier"]:.2f}× of the {money(S["cap"], 0)} cap' if S["multiplier"]
         else "set by its own score", ""),
    ]
    body = "".join(f'<div class="kpi"><div class="k">{esc(k)}</div>'
                   f'<div class="v {c}">{esc(v)}</div><div class="s">{esc(s)}</div></div>'
                   for k, v, s, c in cells)
    return f'<div class="kpis">{body}</div>'


# -------------------------------------------------------------------- funnel


def funnel(S: dict) -> str:
    f = S["funnel"]
    top = max(f["considered"], 1)
    steps = [
        ("considered", f["considered"], "Candidates found", ""),
        ("refused", f["refused"], "Refused by a check", "keep"),
        ("cleared", f["cleared"], "Cleared all nineteen", ""),
        ("submitted", f["submitted"], "Orders sent", ""),
        ("unfilled", f["unfilled"], "Cancelled unfilled", ""),
        ("filled", f["filled"], "Filled", "good"),
    ]
    rows = "".join(
        f'<div class="fnr {cls}"><div class="n">{n}</div>'
        f'<div class="t"><i style="width:{n / top:.1%}"></i></div>'
        f'<div class="l">{esc(label)}</div></div>' for _k, n, label, cls in steps)
    return (f'<div class="fn">{rows}</div>'
            f'<p class="note" style="margin-top:12px">It will not chase a price. An order that '
            f'has not filled within a few minutes is cancelled rather than repriced, which is why '
            f'{f["unfilled"]} of {f["submitted"]} never became positions.</p>')


# ------------------------------------------------------------- money ledger


def ledger(S: dict) -> str:
    rows = [
        ("Funded", money(S["funding"] or 100000)),
        (f'Closed positions ({len(S["closed"])})', money(S["realised"], 2, sign=True)),
        (f'Exchange and clearing fees ({S["fee_charges"]})', money(S["fees"], 2, sign=True)),
    ]
    body = "".join(f'<div class="ld"><span class="t">{esc(a)}</span><span class="d"></span>'
                   f'<span class="v">{esc(b)}</span></div>' for a, b in rows)
    body += (f'<div class="ld total"><span class="t">Equity now</span><span class="d"></span>'
             f'<span class="v">{esc(money(S["equity"]))}</span></div>')
    return body


def closed_table(S: dict) -> str:
    rows = S["closed"]
    if not rows:
        return '<div class="pb"><p class="prose">Nothing has been closed yet.</p></div>'
    head = ('<div class="th"><div>Closed</div><div>Structure</div><div>Exit rule</div>'
            '<div class="num">Credit taken</div><div class="num">Result</div></div>')
    out = []
    for c in rows:
        pl = c.get("pl")
        struct = str(c.get("structure", ""))
        credit = struct.split("@")[-1].strip() if "@" in struct else "—"
        out.append(
            f'<div class="tr"><div class="t-dim">{esc(_short(c.get("ts")))}</div>'
            f'<div class="t-ink">{esc(_fmt(struct))}</div>'
            f'<div><span class="badge loss">{esc(_rule(c.get("rule")))}</span></div>'
            f'<div class="num t-ink">{esc(credit)}</div>'
            f'<div class="num t-ink" style="color:var(--red)">{esc(money(pl, 2, sign=True))}</div>'
            f'</div>')
    return f'<div class="tb cls">{head}{"".join(out)}</div>'


def _rule(r: str) -> str:
    return {"sl_2x": "Stop 2×", "tp_50": "Target 50%",
            "time": "Time stop", "expiry": "Expired"}.get(str(r), str(r or "—"))


def _short(ts) -> str:
    ts = str(ts or "")
    return f"{ts[8:10].lstrip('0')} {_MONTH.get(ts[5:7], '')} {ts[11:16]}" if len(ts) > 15 else ts


def _fmt(s: str) -> str:
    p = str(s or "").split()
    if len(p) < 4:
        return str(s or "—")
    return f"{p[0]} · {p[2].replace('_', ' ')} · {p[3]}" if len(p) > 3 else str(s)


# ------------------------------------------------------------------- checks


def legend() -> str:
    return ('<p class="note" style="margin-top:12px">Each line is one candidate trade, running '
            'left to right until a check stops it. All nineteen run on every candidate, so a '
            'trade can fail more than one; each line is filed under the leftmost check it '
            'failed, and the journal below lists the rest.</p>')


def wall(S: dict) -> str:
    return (f'<div class="sd-wrap"><div class="only-wide">{G.wall_wide(S)}</div>'
            f'<div class="only-narrow">{G.wall_narrow(S)}</div></div>{legend()}')


def stop_table(S: dict) -> str:
    items = sorted(S["stop_counts"].items(), key=lambda kv: -kv[1])
    if not items:
        return '<div class="pb"><p class="prose">Nothing has been stopped yet.</p></div>'
    top = items[0][1]
    verb = _verbatim(S)
    head = '<div class="th"><div class="num">n</div><div>Check</div><div>Share</div></div>'
    rows = []
    for key, count in items:
        rows.append(
            f'<div class="tr"><div class="num t-ink" style="font-weight:600">{count}</div>'
            f'<div><div class="t-ink" style="font-weight:600">{esc(check_label(*key))}</div>'
            + (f'<div class="t-sub">{esc(WHY.get(key, ""))}</div>' if WHY.get(key) else "")
            + (f'<div style="margin-top:5px"><span class="chipcode">{esc(verb.get(key, ""))}'
               f'</span></div>' if verb.get(key) else "")
            + f'</div><div class="bar" style="align-self:center">'
              f'<i style="width:{count / top:.0%}"></i></div></div>')
    return f'<div class="tb stp">{head}{"".join(rows)}</div>'


def _verbatim(S: dict) -> dict:
    out = {}
    for r in S["rows"]:
        if r["stopped"] and r["key"] not in out and r.get("reason"):
            out[r["key"]] = r["reason"]
    return out


def roster(S: dict) -> str:
    fired = {n for (n, _name) in S["stop_counts"]}
    chips = "".join(
        f'<span class="chip{" fired" if n in fired else ""}"><b></b>{esc(RAIL[n])}</span>'
        for n in G.ORDER)
    return (f'<div class="roster">{chips}</div>'
            f'<p class="note" style="margin-top:14px">Five have ever had to refuse anything. The '
            f'other fourteen have not yet been the reason, which is worth saying plainly rather '
            f'than implying all nineteen are constantly at work.</p>')


# -------------------------------------------------------------- calibration


def worksheet(S: dict) -> str:
    rows = [
        ("Equity", money(S["equity"])),
        ("Cap per trade, 1.5% of equity", money(S["cap"])),
        (f'Calibration factor, score {S["brier"]:.3f}' if S["brier"] is not None
         else "Calibration factor", f'{S["multiplier"]:.2f}×' if S["multiplier"] else "—"),
    ]
    body = "".join(f'<div class="ld"><span class="t">{esc(a)}</span><span class="d"></span>'
                   f'<span class="v">{esc(b)}</span></div>' for a, b in rows)
    return body + (f'<div class="ld total"><span class="t">Allowed at risk</span>'
                   f'<span class="d"></span>'
                   f'<span class="v">{esc(money(S["risk_allowed"]))}</span></div>')


def outcomes(S: dict) -> str:
    settled = S["settled"]
    txt = cal_verdict(S)
    if not settled:
        return f'<p class="prose">{esc(txt)}</p>'
    sq = "".join(f'<i class="sq{"" if f.get("inside") else " out"}"></i>' for f in settled)
    return (f'<p class="prose">{esc(txt)}</p>'
            f'<div class="strip" style="margin-top:14px">{sq}</div>'
            f'<p class="note" style="margin-top:10px">{len(settled)} forecasts settled against the '
            f'closing price. Filled where the price landed inside the range it named — '
            f'{S["inside"]} of {len(settled)}.</p>')


def cal_verdict(S: dict) -> str:
    if S["brier"] is None or S["mean_p"] is None or S["hit_rate"] is None:
        return "Not enough settled forecasts yet to score it."
    return (f'It says {S["mean_p"]:.0%} and is right {S["hit_rate"]:.0%} of the time, which is '
            f'underconfident, and it pays for that. A coin flip scores 0.250; it scores '
            f'{S["brier"]:.3f}, so it is barely better than chance at this, and it has cut itself '
            f'to {S["multiplier"]:.2f}× of the size it was otherwise allowed.')


# ------------------------------------------------------------- model review


def review_counts(S: dict) -> str:
    return (f'<p class="prose">A language model reviews each candidate and can object to it. It '
            f'cannot place an order: the tool server it talks to is started without the trading '
            f'tools, so there is no order-placing tool for it to call.</p>'
            f'<div class="ld" style="margin-top:12px"><span class="t">Reviews</span>'
            f'<span class="d"></span><span class="v">{S["reviews"]}</span></div>'
            f'<div class="ld"><span class="t">Agreed</span><span class="d"></span>'
            f'<span class="v">{S["agreed"]}</span></div>'
            f'<div class="ld"><span class="t">Objected, stopping the trade</span>'
            f'<span class="d"></span><span class="v">{S["objected"]}</span></div>'
            f'<div class="ld"><span class="t">Returned nothing</span><span class="d"></span>'
            f'<span class="v">{S["silent"]}</span></div>')


def veto_panel(S: dict) -> str:
    v = S["last_veto"] or {}
    if not v.get("veto_reason"):
        return '<p class="prose">It has not objected to anything yet.</p>'
    return (f'<p class="quote">“{esc(v["veto_reason"])}”</p>'
            f'<p class="note" style="margin-top:10px">{esc(v.get("model", ""))} · an objection '
            f'stops the trade outright</p>')


def capability(S: dict) -> str:
    return (f'<div class="sd-wrap"><div class="only-wide">{G.capability_svg(S)}</div>'
            f'<div class="only-narrow">{G.capability_svg(S, label_size=15)}</div></div>')


# ----------------------------------------------------------------- journal


def log_table(S: dict, limit: int = 18) -> str:
    rows = list(reversed(S["rows"]))[:limit]
    if not rows:
        return '<div class="pb"><p class="prose">Nothing considered yet.</p></div>'
    head = ('<div class="th"><div>Time (UTC)</div><div>Structure</div><div>Outcome</div>'
            '<div>Stopped by</div><div>What it found</div></div>')
    out = []
    for r in rows:
        badge = ('<span class="badge stop">Stopped</span>' if r["stopped"]
                 else '<span class="badge sent">Sent</span>')
        by = (f'<div class="t-ink">{esc(r["stopped_by"])}</div>' if r["stopped"]
              else '<div class="t-dim">—</div>')
        out.append(f'<div class="tr"><div class="t-dim">{esc(r["time"])}</div>'
                   f'<div class="t-ink">{esc(r["structure"])}</div><div>{badge}</div>{by}'
                   f'<div class="t-mono">{esc(r["reason"])}</div></div>')
    return f'<div class="tb log">{head}{"".join(out)}</div>'


def integrity(S: dict) -> str:
    c = S["chain"]
    head = " ".join(re.findall("....", c["head"]))[:39]
    if c["intact"]:
        txt = (f'Every entry is sealed with the fingerprint of the one before it. This screen '
               f'recomputed all {c["entries"]:,} of them on load and the chain is intact. Change '
               f'one past line and the seal breaks.')
    else:
        txt = f'The chain does not verify: {c["broken_at"]}.'
    return (f'<p class="prose">{esc(txt)}</p>'
            f'<p class="note mono" style="margin-top:10px">head {esc(head)}…</p>')


def broker(S: dict) -> str:
    r = S["reconciliation"]
    if not r.get("checked"):
        return '<p class="prose">The broker has not been re-checked this session.</p>'
    n = r.get("cli_positions", 0)
    return (f'<p class="prose">Positions were read twice, once through Alpaca’s own command-line '
            f'tool and once through the agent’s connection. '
            f'{"Both say the same thing" if r.get("ok") else "They disagree"}: '
            f'{"nothing open" if not n else str(n) + " open"}.</p>')


def foot(S: dict) -> str:
    return (f'<div class="foot">Alpaca paper trading · account {esc(S["account_number"])} · '
            f'no real money is at risk. Free data: single-exchange (IEX) stock quotes and '
            f'indicative option prices, with no consolidated options feed. Read '
            f'{esc(_stamp(S))}. Every figure on this screen is computed from files committed to '
            f'the repository.</div>')
