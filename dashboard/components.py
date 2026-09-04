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


LEDE = ("Saadhak is an autonomous options agent trading an Alpaca paper account. "
        "Every few minutes it searches option chains for structures whose worst case is "
        "capped and known before the order is sent. Each candidate is then put to nineteen "
        "independent checks. One failure is enough to stop it, and the reason is written to "
        "a log that cannot be quietly edited.")

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


def _money(x, dp=2) -> str:
    return f"${x:,.{dp}f}" if isinstance(x, (int, float)) else "—"


def plate(S: dict) -> str:
    lamp = "lamp" if S["market_open"] else "lamp off"
    word = "Market open" if S["market_open"] else "Market closed"
    age = f'published {esc(S["age"])} — the account figures below are from that moment' \
        if S["stale"] else f'Account read {esc(_stamp(S))} · {esc(S["age"])}'
    return (f'<div class="plate">'
            f'<span class="dev">साधक</span><i class="vr"></i>'
            f'<span class="wordmark">Saadhak</span>'
            f'<span class="eyebrow">Autonomous options agent · Alpaca paper account '
            f'{esc(S["account_number"])}</span>'
            f'<span class="plate-right">'
            f'<span class="eyebrow"><i class="{lamp}"></i>&nbsp;&nbsp;{word}</span>'
            f'<span class="note">{age}</span>'
            f'</span></div>')


def _stamp(S: dict) -> str:
    raw = str(S.get("as_of") or "")
    return f"{raw[8:10].lstrip('0')} {_MONTH.get(raw[5:7], '')} {raw[11:16]} UTC".strip()


_MONTH = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
          "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}


def verdict(S: dict) -> str:
    since = S["since"]
    move = "down" if (since or 0) < 0 else "up"
    days = _span_days(S)
    money = (f'{_money(S["equity"])} of the {_money(S["start_equity"], 0)} it started with — '
             f'{move} {abs(since):.2%} over {days}.') if since is not None else \
        f'{_money(S["equity"])} in the account.'
    return (f'<div class="verdict"><div>'
            f'<p class="headline">Of the last <span class="n">{S["total"]}</span> trades it '
            f'found, it refused <span class="n">{S["refused"]}</span> — and named the check '
            f'that stopped each one.</p>'
            f'<p class="prose">{LEDE}</p>'
            f'<p class="prose" style="margin-top:14px;color:var(--chalk)">{esc(money)}</p>'
            f'</div><div>'
            f'<div class="tally">'
            f'<div><div class="fig">{S["refused"]}</div><div class="fig-lab">Stopped</div></div>'
            f'<div><div class="fig sent">{S["accepted"]}</div>'
            f'<div class="fig-lab">Sent to the broker</div></div></div>'
            f'<div class="ratio"><span style="flex:{max(S["refused"],1)}"></span>'
            f'<span style="flex:{max(S["accepted"],1)}"></span></div>'
            f'<p class="note" style="margin-top:12px">Nineteen independent checks. '
            f'One failure is enough.</p>'
            f'<div class="sd-wrap" style="margin-top:26px">{G.equity_spark(S)}</div>'
            f'</div></div>')


def _span_days(S: dict) -> str:
    days = len({r["ts"][:10] for r in S["rows"] if r.get("ts")})
    return f"{days} day{'s' if days != 1 else ''}" if days else "the run"


def readouts(S: dict) -> str:
    since = S["since"]
    delta = abs((S["equity"] or 0) - (S["start_equity"] or 0))
    open_n = len(S["open_structures"])
    pct_sent = f'{S["accepted"] / S["total"]:.0%} of what it looked at' if S["total"] else "—"
    cells = [
        ("Equity", _money(S["equity"]), f'started at {_money(S["start_equity"])}'),
        ("Since it started",
         f"{since:+.2%}".replace("-", "−") if since is not None else "—",
         f'{"down" if (since or 0) < 0 else "up"} {_money(delta)} over {_span_days(S)}'),
        ("Open positions", str(open_n) if open_n else "none",
         "the book is flat" if not open_n else "held with a capped worst case"),
        ("Sent / considered", f'{S["accepted"]} / {S["total"]}', pct_sent),
        ("Risk permitted per trade", _money(S["risk_allowed"], 0),
         f'{S["multiplier"]:.2f}× of the {_money(S["cap"], 0)} cap'
         if S["multiplier"] else "set by its own score"),
    ]
    body = "".join(f'<div class="cell"><div class="lbl">{esc(a)}</div>'
                   f'<div class="val mono">{esc(b)}</div>'
                   f'<div class="sub">{esc(c)}</div></div>' for a, b, c in cells)
    return f'<div class="readouts">{body}</div>'


def legend() -> str:
    return ('<div class="legend">'
            '<span><i class="sw-stop"></i>Stopped at this check</span>'
            '<span><i class="sw-pass"></i>Cleared all nineteen</span>'
            '<span><i class="sw-sent"></i>Order sent</span></div>')


def stop_ledger(S: dict) -> str:
    items = sorted(S["stop_counts"].items(), key=lambda kv: -kv[1])
    if not items:
        return ('<div class="empty" style="margin-top:20px"><div class="h">Nothing refused yet'
                '</div><p class="prose" style="margin-top:10px">No candidate has been stopped '
                'so far.</p></div>')
    top = items[0][1]
    verbatim = _verbatim(S)
    rows = []
    for key, count in items:
        why = WHY.get(key, "")
        line = verbatim.get(key, "")
        rows.append(
            f'<div class="stop"><div class="c mono">{count}</div>'
            f'<div><div class="nm">{esc(check_label(*key))}</div>'
            + (f'<div class="why">{esc(why)}</div>' if why else "")
            + (f'<div class="verbatim">in the log — “{esc(line)}”</div>' if line else "")
            + f'</div><div class="bar"><i style="width:{count / top:.0%}"></i></div></div>')
    return f'<div class="stops">{"".join(rows)}</div>'


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
    return f'<div class="roster">{chips}</div>'


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
    return f'<div class="sheet">{body}</div>'


def outcome_strip(S: dict) -> str:
    settled = S["settled"]
    if not settled:
        return ('<p class="note" style="margin-top:22px">No forecasts have settled yet.</p>')
    squares = "".join(f'<i class="sq{"" if f.get("inside") else " out"}"></i>' for f in settled)
    return (f'<div class="strip">{squares}</div>'
            f'<p class="note" style="margin-top:12px">{len(settled)} forecasts, settled against '
            f'the closing price. Filled where the price landed inside the range it named — '
            f'{S["inside"]} of {len(settled)}.</p>')


def cal_verdict(S: dict) -> str:
    if S["brier"] is None or S["mean_p"] is None or S["hit_rate"] is None:
        return "Not enough settled forecasts yet to score it."
    return (f'It says {S["mean_p"]:.0%} and is right {S["hit_rate"]:.0%} of the time — '
            f'underconfident, and it pays for that. A coin flip scores 0.250; it scores '
            f'{S["brier"]:.3f}, so it is barely better than chance at this, and it has cut '
            f'itself to {S["multiplier"]:.2f}\u00d7 of the size it was otherwise allowed.')


def capability_panel(S: dict) -> str:
    veto = S["last_veto"] or {}
    last = S["last_review"] or {}
    panels = [
        f'<div class="panel"><div class="eyebrow">{S["reviews"]} reviews</div>'
        f'<p class="prose" style="margin-top:10px">Agreed {S["agreed"]} · objected '
        f'{S["objected"]} · returned nothing {S["silent"]}.</p></div>']
    if veto.get("veto_reason"):
        panels.append(
            f'<div class="panel"><div class="eyebrow">The last time it objected, in its own '
            f'words</div><p class="quote" style="margin-top:12px">{esc(veto["veto_reason"])}</p>'
            f'<p class="note" style="margin-top:12px">{esc(veto.get("model", ""))} · an objection '
            f'stops the trade</p></div>')
    panels.append(f'<div class="panel"><div class="eyebrow">The most recent review</div>'
                  f'<p class="prose" style="margin-top:10px">{esc(_last_sentence(last))}</p></div>')
    return (f'<div class="duo"><div class="sd-wrap">'
            f'<div class="only-wide">{G.capability_svg(S)}</div>'
            f'<div class="only-narrow">{G.capability_svg(S, label_size=15)}</div></div>'
            f'<div>{"".join(panels)}</div></div>')


def _last_sentence(last: dict) -> str:
    if not last:
        return "No review has been recorded yet."
    verdict_ = last.get("verdict")
    if verdict_ == "veto":
        return "The most recent review objected, and the trade was stopped."
    if verdict_ == "agree":
        return "The most recent review agreed with the engine, which does not by itself " \
               "permit anything; the checks still decide."
    return ("The most recent review returned nothing — the model spent its whole token budget "
            "reasoning and produced no answer. That is recorded as a failure, never as "
            "agreement, and the trade was decided on the checks alone.")


def decision_log(S: dict, limit: int = 24) -> str:
    rows = list(reversed(S["rows"]))[:limit]
    if not rows:
        return ('<div class="empty"><div class="h">No decisions yet</div>'
                '<p class="prose" style="margin-top:10px">Nothing has been considered so far.'
                '</p></div>')
    head = ('<div class="head"><div>Time (UTC)</div><div>Structure</div><div>Outcome</div>'
            '<div>Stopped by</div><div>What it found</div></div>')
    body = []
    for r in rows:
        badge = ('<div class="b stopped"><i></i>Stopped</div>' if r["stopped"]
                 else '<div class="b sent"><i></i>Sent</div>')
        stopped_by = (f'<div class="k">{esc(r["stopped_by"])}</div>' if r["stopped"]
                      else '<div class="k none">—</div>')
        body.append(f'<div class="row"><div class="t mono">{esc(r["time"])}</div>'
                    f'<div class="s mono">{esc(r["structure"])}</div>{badge}{stopped_by}'
                    f'<div class="r mono">{esc(r["reason"])}</div></div>')
    more = (f'<p class="note" style="margin-top:14px">Showing the most recent {len(rows)} of '
            f'{S["total"]}. All of them are in the committed log.</p>'
            if S["total"] > len(rows) else "")
    return f'<div class="log">{head}{"".join(body)}</div>{more}'


def record_panel(S: dict) -> str:
    chain = S["chain"]
    if chain["intact"]:
        chain_txt = (f'Every entry is sealed with the fingerprint of the entry before it. This '
                     f'page recomputed all {chain["entries"]:,} fingerprints when it loaded, and '
                     f'the chain is intact. Change one past line and the seal breaks.')
        chain_style = ""
    else:
        chain_txt = f'The chain does not verify: {chain["broken_at"]}.'
        chain_style = ' style="color:var(--oxide)"'
    head = " ".join(re.findall("....", chain["head"]))[:59]

    rec = S["reconciliation"]
    if rec.get("checked"):
        agree = "Both say the same thing" if rec.get("ok") else "They disagree"
        n = rec.get("cli_positions", 0)
        what = "nothing open" if not n else f"{n} open"
        recon = (f'Positions were read twice, once through Alpaca’s own command-line tool and '
                 f'once through the agent’s connection. {agree}: {what}.')
        lamp = "lamp" if rec.get("ok") else "lamp fault"
    else:
        recon, lamp = "The broker has not been re-checked this session.", "lamp off"

    open_n = len(S["open_structures"])
    flat = (f'The book is flat, so there is nothing to close. It may lose at most '
            f'{_money(S["risk_allowed"], 0)} on the next trade, and every structure is built '
            f'with a bought wing, so the worst case is capped before the order goes out.')
    open_block = (f'<div class="empty" style="margin-top:20px"><div class="h">Nothing open</div>'
                  f'<p class="prose" style="margin-top:10px">{esc(flat)}</p></div>'
                  if not open_n else _open_block(S))

    routing = "".join(
        f'<p class="note" style="margin-top:8px">{esc(m)} — {esc(lim.get("rate_per_min"))}/min · '
        f'{esc(lim.get("allowed"))} sent, {esc(lim.get("throttled_by_provider"))} throttled</p>'
        for m, lim in sorted(S["limiters"].items()) if m != "default")

    return (f'<div class="duo" style="margin-top:24px"><div>'
            f'<div class="panel"><div class="eyebrow">The log checks out</div>'
            f'<p class="prose"{chain_style} style="margin-top:10px">{esc(chain_txt)}</p>'
            f'<p class="note" style="margin-top:10px">head {esc(head)}…</p></div>'
            f'<div class="panel"><div class="eyebrow"><i class="{lamp}"></i>&nbsp;&nbsp;'
            f'The broker agrees</div>'
            f'<p class="prose" style="margin-top:10px">{esc(recon)}</p></div>'
            f'</div><div>{open_block}'
            + (f'<div class="panel" style="margin-top:20px">'
               f'<div class="eyebrow">Which model answered</div>{routing}'
               f'<p class="note" style="margin-top:10px">Each model has its own measured rate. '
               f'When one is throttled, the next answers.</p></div>' if routing else "")
            + '</div></div>')


def _open_block(S: dict) -> str:
    rows = "".join(
        f'<div class="ld"><span class="t">{esc(o.get("describe"))}</span><span class="d"></span>'
        f'<span class="v">{esc(_money(o.get("unrealised")))}</span></div>'
        for o in S["open_structures"])
    return (f'<div class="panel"><div class="eyebrow">Open positions</div>'
            f'<div class="sheet" style="margin-top:12px">{rows}</div></div>')


def footer(S: dict) -> str:
    return (f'<div class="footer">Alpaca paper trading. No real money is at risk. '
            f'Free data: single-exchange (IEX) stock quotes and indicative option prices, with '
            f'no consolidated options feed. Account read {esc(_stamp(S))}. '
            f'Every number on this page is computed from files committed to this repository.'
            f'</div>')
