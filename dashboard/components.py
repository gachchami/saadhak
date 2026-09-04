"""Every block of HTML on the page, and the words in it.

One rule about language: nothing here names a check by number or by the
identifier it has in the code. A reader who has never seen this project should
be able to read the whole page.
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


SUB = ("Saadhak is an autonomous options agent trading an Alpaca paper account. Every few "
       "minutes it searches option chains for structures whose worst case is capped and known "
       "before the order is sent. Each candidate is then put to nineteen independent checks. "
       "One failure is enough to stop it, and the reason is written to a log that cannot be "
       "quietly edited.")

HERO_CAPTION = ("Each line is one candidate trade, running left to right until a check stops it. "
                "All nineteen checks run on every candidate, so a trade can fail more than one; "
                "each line is filed under the leftmost check it failed, and the log below lists "
                "the rest.")

STOPS_LEAD = ("Five of the nineteen checks have ever had to refuse anything. The other fourteen "
              "have not yet been the reason, which is worth saying plainly rather than implying "
              "all nineteen are constantly at work.")

CAL_LEAD = ("The agent states a probability on every forecast it makes. Those forecasts are "
            "settled against the closing price, scored, and the score decides how much money "
            "the next trade is allowed to lose. Being confidently wrong shrinks its own "
            "position size.")

MODEL_LEAD = ("A language model reviews each candidate and can object to it. It cannot place an "
              "order. The tool server it talks to is started without the trading tools, so there "
              "is no order-placing tool for it to call.")

RECORD_LEAD = ("Every decision, including the ones it declined, with the check that stopped it "
               "and what that check found.")

_MONTH = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
          "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}


def _money(x, dp=2) -> str:
    return f"${x:,.{dp}f}" if isinstance(x, (int, float)) else "—"


def _stamp(S: dict) -> str:
    raw = str(S.get("as_of") or "")
    return f"{raw[8:10].lstrip('0')} {_MONTH.get(raw[5:7], '')} {raw[11:16]} UTC".strip()


def _span_days(S: dict) -> str:
    days = len({r["ts"][:10] for r in S["rows"] if r.get("ts")})
    return f"{days} day{'s' if days != 1 else ''}" if days else "the run"


def section(eyebrow: str, heading: str, lead: str = "") -> str:
    return (f'<div class="sec"><div class="eyebrow">{esc(eyebrow)}</div>'
            f'<div class="h2">{esc(heading)}</div>'
            + (f'<p class="lead">{esc(lead)}</p>' if lead else "") + "</div>")


# ------------------------------------------------------------------- top bar


def bar(S: dict) -> str:
    live = S["market_open"]
    return (f'<div class="bar"><span class="mark"><span class="dev">साधक</span>'
            f'<span class="wordmark">Saadhak</span></span>'
            f'<span class="tag">Autonomous options agent · Alpaca paper account '
            f'{esc(S["account_number"])}</span>'
            f'<span class="right">'
            f'<span class="pill{"" if live else " off"}"><i></i>'
            f'{"Market open" if live else "Market closed"}</span>'
            f'<span class="note">Read {esc(_stamp(S))} · {esc(S["age"])}</span>'
            f'</span></div>')


# --------------------------------------------------------------------- hero


def hero(S: dict) -> str:
    return (f'<div class="hero">'
            f'<div class="eyebrow">Defined-risk options · paper trading</div>'
            f'<h1>It refused <em>{S["refused"]}</em> of the last {S["total"]} trades it found.</h1>'
            f'<p class="sub">And it can name the check that stopped every one of them. {esc(SUB)}</p>'
            f'</div>')


def tally_card(S: dict) -> str:
    return (f'<div class="card pad raised">'
            f'<div class="tally">'
            f'<div><div class="fig">{S["refused"]}</div><div class="fig-k">Stopped</div></div>'
            f'<div><div class="fig go">{S["accepted"]}</div>'
            f'<div class="fig-k">Sent to the broker</div></div></div>'
            f'<div class="ratio"><span style="flex:{max(S["refused"],1)}"></span>'
            f'<span style="flex:{max(S["accepted"],1)}"></span></div>'
            f'<p class="note" style="margin-top:14px">Nineteen independent checks run on every '
            f'candidate. One failure is enough.</p>'
            f'<div class="sd-wrap" style="margin-top:22px">{G.equity_spark(S)}</div>'
            f'</div>')


def stats(S: dict) -> str:
    since = S["since"]
    delta = abs((S["equity"] or 0) - (S["start_equity"] or 0))
    open_n = len(S["open_structures"])
    cells = [
        ("Equity", _money(S["equity"]), f'started at {_money(S["start_equity"])}', ""),
        ("Since it started",
         f"{since:+.2%}" if since is not None else "—",
         f'{"down" if (since or 0) < 0 else "up"} {_money(delta)} over {_span_days(S)}',
         "neg" if (since or 0) < 0 else "pos"),
        ("Open positions", str(open_n) if open_n else "None",
         "the book is flat" if not open_n else "worst case capped", ""),
        ("Sent / considered", f'{S["accepted"]} / {S["total"]}',
         f'{S["accepted"] / S["total"]:.0%} of what it looked at' if S["total"] else "—", ""),
        ("Risk allowed per trade", _money(S["risk_allowed"], 0),
         f'{S["multiplier"]:.2f}× of the {_money(S["cap"], 0)} cap'
         if S["multiplier"] else "set by its own score", ""),
    ]
    body = "".join(f'<div class="stat"><div class="k">{esc(k)}</div>'
                   f'<div class="v {cls}">{esc(v)}</div>'
                   f'<div class="s">{esc(s)}</div></div>' for k, v, s, cls in cells)
    return f'<div class="card stats" style="margin-top:26px">{body}</div>'


# --------------------------------------------------------------------- hero graphic


def legend() -> str:
    return ('<div class="legend">'
            '<span><i class="sw-stop"></i>Stopped at this check</span>'
            '<span><i class="sw-pass"></i>Cleared all nineteen</span>'
            '<span><i class="sw-sent"></i>Order sent</span></div>')


def wall_card(S: dict) -> str:
    return (f'<div class="card pad sd-wrap">'
            f'<div class="only-wide">{G.wall_wide(S)}</div>'
            f'<div class="only-narrow">{G.wall_narrow(S)}</div>'
            f'{legend()}'
            f'<p class="note" style="margin-top:16px;max-width:78ch">{esc(HERO_CAPTION)}</p>'
            f'</div>')


# --------------------------------------------------------------- what stopped them


def stop_ledger(S: dict) -> str:
    items = sorted(S["stop_counts"].items(), key=lambda kv: -kv[1])
    if not items:
        return ('<div class="card pad"><div class="stop .nm">Nothing has been stopped yet.</div>'
                '</div>')
    top = items[0][1]
    verbatim = _verbatim(S)
    rows = []
    for key, count in items:
        why = WHY.get(key, "")
        line = verbatim.get(key, "")
        rows.append(
            f'<div class="stop"><div class="c">{count}</div>'
            f'<div><div class="nm">{esc(check_label(*key))}</div>'
            + (f'<div class="why">{esc(why)}</div>' if why else "")
            + (f'<div class="verbatim">{esc(line)}</div>' if line else "")
            + f'</div><div class="bar"><i style="width:{count / top:.0%}"></i></div></div>')
    return f'<div class="card">{"".join(rows)}</div>'


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
    return (f'<div style="margin-top:22px"><div class="eyebrow plain" style="margin-bottom:10px">'
            f'All nineteen checks</div><div class="roster">{chips}</div></div>')


# ------------------------------------------------------------------ calibration


def worksheet(S: dict) -> str:
    rows = [
        ("Equity in the account", _money(S["equity"])),
        ("Most it may lose on one trade, 1.5% of equity", _money(S["cap"])),
        (f'Calibration factor, from a score of {S["brier"]:.3f}' if S["brier"] is not None
         else "Calibration factor, from the opening prior",
         f'{S["multiplier"]:.2f}×' if S["multiplier"] else "—"),
    ]
    body = "".join(f'<div class="ld"><span class="t">{esc(a)}</span>'
                   f'<span class="d"></span><span class="v">{esc(b)}</span></div>'
                   for a, b in rows)
    body += (f'<div class="ld total"><span class="t">Permitted at risk on the next trade</span>'
             f'<span class="d"></span><span class="v">{esc(_money(S["risk_allowed"]))}</span></div>')
    return f'<div class="card pad">{body}</div>'


def outcome_card(S: dict) -> str:
    settled = S["settled"]
    inner = (f'<p class="prose">{esc(cal_verdict(S))}</p>')
    if settled:
        squares = "".join(f'<i class="sq{"" if f.get("inside") else " out"}"></i>' for f in settled)
        inner += (f'<div class="strip" style="margin-top:20px">{squares}</div>'
                  f'<p class="note" style="margin-top:12px">{len(settled)} forecasts, settled '
                  f'against the closing price. Filled where the price landed inside the range it '
                  f'named — {S["inside"]} of {len(settled)}.</p>')
    else:
        inner += '<p class="note" style="margin-top:16px">No forecasts have settled yet.</p>'
    return f'<div class="card pad">{inner}</div>'


def cal_verdict(S: dict) -> str:
    if S["brier"] is None or S["mean_p"] is None or S["hit_rate"] is None:
        return "Not enough settled forecasts yet to score it."
    return (f'It says {S["mean_p"]:.0%} and is right {S["hit_rate"]:.0%} of the time, which is '
            f'underconfident, and it pays for that. A coin flip scores 0.250; it scores '
            f'{S["brier"]:.3f}, so it is barely better than chance at this, and it has cut '
            f'itself to {S["multiplier"]:.2f}× of the size it was otherwise allowed.')


def loop_card(S: dict) -> str:
    return f'<div class="card pad sd-wrap">{G.loop_wide(S)}</div>'


# ----------------------------------------------------------------- the model


def capability_section(S: dict) -> str:
    veto = S["last_veto"] or {}
    last = S["last_review"] or {}
    panels = [
        f'<div class="card pad"><div class="eyebrow plain">{S["reviews"]} reviews</div>'
        f'<p class="prose" style="margin-top:8px">Agreed {S["agreed"]} · objected '
        f'{S["objected"]} · returned nothing {S["silent"]}.</p></div>']
    if veto.get("veto_reason"):
        panels.append(
            f'<div class="card pad" style="margin-top:20px">'
            f'<div class="eyebrow plain">The last time it objected, in its own words</div>'
            f'<p class="quote" style="margin-top:12px">“{esc(veto["veto_reason"])}”</p>'
            f'<p class="note" style="margin-top:12px">{esc(veto.get("model", ""))} · an objection '
            f'stops the trade</p></div>')
    panels.append(f'<div class="card pad" style="margin-top:20px">'
                  f'<div class="eyebrow plain">The most recent review</div>'
                  f'<p class="prose" style="margin-top:8px">{esc(_last_sentence(last))}</p></div>')
    return (f'<div class="grid37">'
            f'<div class="card pad sd-wrap"><div class="only-wide">{G.capability_svg(S)}</div>'
            f'<div class="only-narrow">{G.capability_svg(S, label_size=15)}</div></div>'
            f'<div>{"".join(panels)}</div></div>')


def _last_sentence(last: dict) -> str:
    if not last:
        return "No review has been recorded yet."
    verdict_ = last.get("verdict")
    if verdict_ == "veto":
        return "The most recent review objected, and the trade was stopped."
    if verdict_ == "agree":
        return ("The most recent review agreed with the engine, which does not by itself permit "
                "anything; the checks still decide.")
    return ("The most recent review returned nothing — the model spent its whole token budget "
            "reasoning and produced no answer. That is recorded as a failure, never as "
            "agreement, and the trade was decided on the checks alone.")


# ---------------------------------------------------------------- the record


def decision_log(S: dict, limit: int = 20) -> str:
    rows = list(reversed(S["rows"]))[:limit]
    if not rows:
        return '<div class="card pad"><p class="prose">Nothing has been considered yet.</p></div>'
    head = ('<div class="head"><div>Time (UTC)</div><div>Structure</div><div>Outcome</div>'
            '<div>Stopped by</div><div>What it found</div></div>')
    body = []
    for r in rows:
        badge = ('<div><span class="badge stopped">Stopped</span></div>' if r["stopped"]
                 else '<div><span class="badge sent">Sent</span></div>')
        stopped_by = (f'<div class="k">{esc(r["stopped_by"])}</div>' if r["stopped"]
                      else '<div class="k none">—</div>')
        body.append(f'<div class="row"><div class="t">{esc(r["time"])}</div>'
                    f'<div class="s">{esc(r["structure"])}</div>{badge}{stopped_by}'
                    f'<div class="r">{esc(r["reason"])}</div></div>')
    more = (f'<p class="note" style="margin-top:14px">Showing the most recent {len(rows)} of '
            f'{S["total"]}. All of them are in the committed log.</p>'
            if S["total"] > len(rows) else "")
    return f'<div class="card log">{head}{"".join(body)}</div>{more}'


def record_section(S: dict) -> str:
    chain = S["chain"]
    if chain["intact"]:
        chain_txt = (f'Every entry is sealed with the fingerprint of the entry before it. This '
                     f'page recomputed all {chain["entries"]:,} fingerprints when it loaded, and '
                     f'the chain is intact. Change one past line and the seal breaks.')
        chain_pill = '<span class="pill"><i></i>Verified</span>'
    else:
        chain_txt = f'The chain does not verify: {chain["broken_at"]}.'
        chain_pill = '<span class="pill off"><i></i>Broken</span>'
    head = " ".join(re.findall("....", chain["head"]))[:39]

    rec = S["reconciliation"]
    if rec.get("checked"):
        agree = "Both say the same thing" if rec.get("ok") else "They disagree"
        n = rec.get("cli_positions", 0)
        recon = (f'Positions were read twice, once through Alpaca’s own command-line tool and '
                 f'once through the agent’s connection. {agree}: '
                 f'{"nothing open" if not n else str(n) + " open"}.')
        recon_pill = ('<span class="pill"><i></i>Agree</span>' if rec.get("ok")
                      else '<span class="pill off"><i></i>Mismatch</span>')
    else:
        recon = "The broker has not been re-checked this session."
        recon_pill = '<span class="pill off"><i></i>Not checked</span>'

    routing = "".join(
        f'<p class="note" style="margin-top:6px">{esc(m)} — {esc(lim.get("rate_per_min"))}/min · '
        f'{esc(lim.get("allowed"))} sent, {esc(lim.get("throttled_by_provider"))} throttled</p>'
        for m, lim in sorted(S["limiters"].items()) if m != "default")

    third = (f'<div class="card pad"><div class="eyebrow plain">Which model answered</div>'
             f'{routing}<p class="note" style="margin-top:10px">Each model has its own measured '
             f'rate. When one is throttled, the next answers.</p></div>') if routing else (
        f'<div class="card pad"><div class="eyebrow plain">Nothing open</div>'
        f'<p class="prose" style="margin-top:8px">The book is flat, so there is nothing to close. '
        f'It may lose at most {esc(_money(S["risk_allowed"], 0))} on the next trade, and every '
        f'structure is built with a bought wing, so the worst case is capped before the order '
        f'goes out.</p></div>')

    return (f'<div class="grid2" style="margin-top:20px">'
            f'<div class="card pad"><div style="display:flex;align-items:center;gap:12px">'
            f'<div class="eyebrow plain">The log checks out</div>{chain_pill}</div>'
            f'<p class="prose" style="margin-top:10px">{esc(chain_txt)}</p>'
            f'<p class="note mono" style="margin-top:10px">head {esc(head)}…</p></div>'
            f'<div class="card pad"><div style="display:flex;align-items:center;gap:12px">'
            f'<div class="eyebrow plain">The broker agrees</div>{recon_pill}</div>'
            f'<p class="prose" style="margin-top:10px">{esc(recon)}</p></div>'
            f'</div><div style="margin-top:20px">{third}</div>')


def foot(S: dict) -> str:
    return (f'<div class="foot">Alpaca paper trading. No real money is at risk. '
            f'Free data: single-exchange (IEX) stock quotes and indicative option prices, with '
            f'no consolidated options feed. Account read {esc(_stamp(S))}. '
            f'Every number on this page is computed from files committed to this repository.'
            f'</div>')
