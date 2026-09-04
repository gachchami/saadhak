"""Hand-authored inline SVG. No chart library, no runtime, no external images.

Colours are written as literals rather than custom properties so the drawings
survive being copied out of the page into a slide or a screenshot.
"""
from __future__ import annotations

# Drawn on white, in the page's palette. CHALK is the refusal mass, which on a
# light ground is the darkest ink rather than the brightest.
GROUND, PANEL, RULE = "#FFFFFF", "#F6F9FC", "#E3E8EE"
CHALK, SLATE, DIM = "#0A2540", "#697386", "#8792A2"
TRACK, VERDIGRIS, OXIDE = "#C9D3DF", "#0E7C66", "#CD3D64"

SANS = "'Instrument Sans',Helvetica,Arial,sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,Menlo,monospace"

# The engine runs every check on every candidate rather than stopping at the
# first failure, so left-to-right cannot honestly claim to be running order.
# Grouping by the question each check answers is both truer and easier to read.
GROUPS = [
    ("MAY WE TRADE AT ALL", [1, 6, 17, 16]),
    ("IS THIS TRADE ALLOWED", [2, 10, 11, 18, 19]),
    ("IS THE TRADE SOUND", [3, 4, 5, 7, 8, 9, 12]),
    ("IS THE ORDER SAFE", [13, 14, 15]),
]
RAIL = {
    1: "Market hours", 6: "Loss halts clear", 17: "Kill switch clear", 16: "Broker agrees",
    2: "Approved symbol", 10: "Time to expiry", 11: "No event due", 18: "No losing streak",
    19: "Not a repeat bet",
    3: "Risk is capped", 4: "Worst case fits", 5: "Book has room", 7: "Both sides liquid",
    8: "Premium vs odds", 9: "Strike data", 12: "At least one lot",
    13: "One order, one id", 14: "Limit orders only", 15: "Exit plan attached",
}
ORDER = [n for _, ns in GROUPS for n in ns]
SLOT = {n: i for i, n in enumerate(ORDER)}
POST_X = [186, 230, 274, 318, 384, 428, 472, 516, 560,
          626, 670, 714, 758, 802, 846, 890, 956, 1000, 1044]


def _t(x, y, s, *, fill=CHALK, size=11, family=SANS, weight="600",
       anchor="start", ls=None, extra="") -> str:
    sp = f' letter-spacing="{ls}"' if ls else ""
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{sp}{extra}>{s}</text>')


def _ordered(S: dict) -> tuple[list[dict], dict]:
    """Refused first, by the check that stopped them; then the ones that went through."""
    counts: dict[int, int] = {}
    for (n, _name), c in S["stop_counts"].items():
        counts[n] = counts.get(n, 0) + c
    stopped = [r for r in S["rows"] if r["stopped"]]
    passed = [r for r in S["rows"] if not r["stopped"]]
    stopped.sort(key=lambda r: SLOT.get((r["key"] or (99,))[0], 99))
    return stopped + passed, counts


def wall_wide(S: dict) -> str:
    rows, counts = _ordered(S)
    n = len(rows)
    total, refused, sent = S["total"], S["refused"], S["accepted"]
    if not rows:
        return _empty_wall()

    top, bottom = 76.0, 457.0
    shown = rows[-130:] if n > 130 else rows
    pitch = min(8.0, (bottom - top) / max(len(shown) - 1, 1))
    bar_h = max(2.0, min(5.0, pitch - 3))

    out = [f'<svg viewBox="0 0 1240 600" width="100%" height="auto" '
           f'preserveAspectRatio="xMidYMid meet" role="img" '
           f'xmlns="http://www.w3.org/2000/svg">'
           f'<title>Every candidate trade and the check that stopped it</title>'
           f'<desc>{total} candidate trades were considered. {refused} were stopped '
           f'before any order was sent and {sent} were sent to the broker.</desc>']

    # group headers and their rules
    for title, ns in GROUPS:
        xs = [POST_X[SLOT[m]] for m in ns]
        out.append(_t(xs[0] - 22, 24, title, fill=DIM, size=10.5, ls=1.7))
        out.append(f'<line x1="{xs[0]-22}" y1="32" x2="{xs[-1]+22}" y2="32" '
                   f'stroke="{RULE}" stroke-width="1" vector-effect="non-scaling-stroke"/>')

    # posts, their counts, and their labels
    for i, num in enumerate(ORDER):
        x, hits = POST_X[i], counts.get(num, 0)
        if hits:
            out.append(f'<line x1="{x}" y1="54" x2="{x}" y2="470" stroke="{CHALK}" '
                       f'stroke-width="1.5" vector-effect="non-scaling-stroke"/>')
            out.append(_t(x, 46, hits, fill=CHALK, size=15, family=MONO,
                          weight="500", anchor="middle"))
        else:
            out.append(f'<line x1="{x}" y1="62" x2="{x}" y2="464" stroke="{RULE}" '
                       f'stroke-width="1" vector-effect="non-scaling-stroke"/>')
        out.append(_t(0, 0, RAIL.get(num, ""), fill=CHALK if hits else DIM, size=10,
                      weight="500", anchor="end", ls=0.2,
                      extra=f' transform="translate({x + 3.4},474) rotate(-90)"'))

    out.append(f'<line x1="158" y1="466" x2="1078" y2="466" stroke="{RULE}" '
               f'stroke-width="1" vector-effect="non-scaling-stroke"/>')

    # the rows: one line per candidate, running until something stops it
    for i, r in enumerate(shown):
        y = top + pitch * i
        if r["stopped"]:
            x_stop = POST_X[SLOT.get((r["key"] or (99,))[0], 18)]
            out.append(f'<rect x="158" y="{y:.1f}" width="{x_stop - 158}" '
                       f'height="{bar_h:.1f}" rx="1.5" fill="{CHALK}"/>')
        else:
            out.append(f'<line x1="158" y1="{y + bar_h / 2:.1f}" x2="1078" '
                       f'y2="{y + bar_h / 2:.1f}" stroke="{TRACK}" stroke-width="1.5" '
                       f'vector-effect="non-scaling-stroke"/>')
            out.append(f'<rect x="1082" y="{y - 0.5:.1f}" width="6" height="6" fill="{VERDIGRIS}"/>')

    # margins: what came in, what was stopped, what went out
    out.append(f'<path d="M154 76 H148 V457 H154" stroke="{TRACK}" stroke-width="1" fill="none"/>')
    out.append(_t(138, 250, total, fill=CHALK, size=40, family=MONO, weight="500", anchor="end"))
    out.append(_t(138, 268, "CANDIDATE TRADES", fill=DIM, size=10.5, anchor="end", ls=1.4))
    out.append(_t(138, 281, "CONSIDERED", fill=DIM, size=10.5, anchor="end", ls=1.4))

    split = top + pitch * max(len(shown) - sent, 0)
    out.append(f'<path d="M1092 76 h6 M1092 76 V{split:.0f} M1092 {split:.0f} h6" '
               f'stroke="{CHALK}" stroke-opacity=".45" stroke-width="1" fill="none"/>')
    out.append(_t(1106, 220, refused, fill=CHALK, size=40, family=MONO, weight="500"))
    out.append(_t(1106, 238, "STOPPED", fill=DIM, size=10.5, ls=1.4))
    out.append(_t(1106, 251, "BEFORE ANY ORDER", fill=DIM, size=10.5, ls=1.4))

    out.append(f'<path d="M1092 {split + 3:.0f} h6 M1092 {split + 3:.0f} V457 M1092 457 h6" '
               f'stroke="{VERDIGRIS}" stroke-opacity=".5" stroke-width="1" fill="none"/>')
    out.append(_t(1106, 404, sent, fill=VERDIGRIS, size=40, family=MONO, weight="500"))
    out.append(_t(1106, 422, "SENT TO", fill=DIM, size=10.5, ls=1.4))
    out.append(_t(1106, 435, "THE BROKER", fill=DIM, size=10.5, ls=1.4))

    if n > 130:
        out.append(_t(158, 592, f"showing the most recent 130 of {n}", fill=DIM, size=10.5, ls=1.4))
    out.append("</svg>")
    return "".join(out)


def wall_narrow(S: dict) -> str:
    rows, counts = _ordered(S)
    if not rows:
        return _empty_wall()
    px = [30 + 16.6 * i for i in range(19)]
    shown = rows[-52:]
    pitch = min(7.0, 340 / max(len(shown), 1))
    bar_h = max(2.0, min(4.0, pitch - 2))
    out = [f'<svg viewBox="0 0 358 430" width="100%" height="auto" role="img" '
           f'xmlns="http://www.w3.org/2000/svg">'
           f'<title>Every candidate trade and the check that stopped it</title>'
           f'<desc>{S["total"]} considered, {S["refused"]} stopped, {S["accepted"]} sent.</desc>']
    for i, num in enumerate(ORDER):
        hits = counts.get(num, 0)
        if hits:
            out.append(f'<line x1="{px[i]:.1f}" y1="50" x2="{px[i]:.1f}" y2="396" '
                       f'stroke="{CHALK}" stroke-width="1.25" vector-effect="non-scaling-stroke"/>')
            out.append(_t(f"{px[i]:.1f}", 42, hits, fill=CHALK, size=10, family=MONO,
                          weight="500", anchor="middle"))
        else:
            out.append(f'<line x1="{px[i]:.1f}" y1="56" x2="{px[i]:.1f}" y2="396" '
                       f'stroke="{RULE}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    for i, r in enumerate(shown):
        y = 56 + pitch * i
        if r["stopped"]:
            x_stop = px[SLOT.get((r["key"] or (99,))[0], 18)]
            out.append(f'<rect x="14" y="{y:.1f}" width="{x_stop - 14:.1f}" '
                       f'height="{bar_h:.1f}" rx="1.5" fill="{CHALK}"/>')
        else:
            out.append(f'<line x1="14" y1="{y + bar_h / 2:.1f}" x2="340" y2="{y + bar_h / 2:.1f}" '
                       f'stroke="{TRACK}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
            out.append(f'<rect x="344" y="{y:.1f}" width="4" height="4" fill="{VERDIGRIS}"/>')
    out.append(f'<line x1="14" y1="404" x2="348" y2="404" stroke="{RULE}" stroke-width="1"/>')
    out.append(_t(14, 422, f'{S["refused"]} STOPPED · {S["accepted"]} SENT', fill=DIM, size=10, ls=1.2))
    out.append("</svg>")
    return "".join(out)


def _empty_wall() -> str:
    return (f'<svg viewBox="0 0 1240 200" width="100%" height="auto" role="img" '
            f'xmlns="http://www.w3.org/2000/svg"><title>No decisions yet</title>'
            f'<rect x="158" y="20" width="920" height="140" fill="none" stroke="{RULE}" '
            f'stroke-dasharray="4 4"/>'
            + _t(618, 96, "NO DECISIONS RECORDED YET", fill=DIM, size=12, anchor="middle", ls=1.8)
            + "</svg>")


def _head(x, y, d=1) -> str:
    """A small solid arrowhead. An explicit polygon, never a marker element."""
    return f'<polygon points="{x},{y} {x - 7 * d},{y - 3.5} {x - 7 * d},{y + 3.5}" fill="{SLATE}"/>'


def loop_wide(S: dict) -> str:
    inside, n = S["inside"], len(S["settled"])
    stations = [
        ("IT STATES A PROBABILITY", _pct(S["mean_p"]), "average of its last 40 forecasts"),
        ("THE MARKET SETTLES IT", f"{inside} of {n}" if n else "none yet",
         "closed inside the range it named"),
        ("THE GAP IS SCORED", f'{S["brier"]:.3f}' if S["brier"] is not None else "—",
         "a coin flip scores 0.250"),
        ("THE NEXT TRADE IS SIZED",
         f'${S["risk_allowed"]:,.0f}' if S["risk_allowed"] else "—",
         f'{S["multiplier"]:.2f}\u00d7 of the ${S["cap"]:,.0f} cap' if S["multiplier"] else ""),
    ]
    xs = [20, 337, 654, 970]
    out = ['<svg viewBox="0 0 1240 196" width="100%" height="auto" role="img" '
           'xmlns="http://www.w3.org/2000/svg">'
           '<title>How the agent earns the size it may risk</title>'
           '<desc>It states a probability, the market settles it, the gap is scored, '
           'and the score sets the money allowed on the next trade.</desc>']
    for i, (eyebrow, value, note) in enumerate(stations):
        x = xs[i]
        out.append(f'<rect x="{x}" y="28" width="250" height="92" rx="8" fill="{PANEL}" '
                   f'stroke="{RULE}" stroke-width="1"/>')
        out.append(_t(x + 16, 50, eyebrow, fill=DIM, size=10, ls=1.5))
        out.append(_t(x + 16, 86, value, fill=CHALK, size=26, family=MONO, weight="500"))
        out.append(_t(x + 16, 106, note, fill=SLATE, size=11, family=MONO, weight="400"))
        if i < 3:
            out.append(f'<line x1="{x + 258}" y1="74" x2="{xs[i+1] - 15}" y2="74" '
                       f'stroke="{SLATE}" stroke-width="1"/>' + _head(xs[i + 1] - 8, 74))
    out.append(f'<path d="M1220 74 h8 v82 H12 V74 h8" stroke="{VERDIGRIS}" '
               f'stroke-width="1.5" fill="none"/>'
               f'<polygon points="20,74 13,70.5 13,77.5" fill="{VERDIGRIS}"/>')
    out.append(_t(620, 178, "EVERY SCORED FORECAST CHANGES THE NEXT POSITION SIZE",
                  fill=VERDIGRIS, size=10.5, anchor="middle", ls=1.6))
    out.append("</svg>")
    return "".join(out)


def capability_svg(S: dict, *, label_size=13) -> str:
    tools = S["tools"] or []
    k = max(len(tools), 1)
    height = max(210, 30 + 54 * k + 90)
    out = [f'<svg viewBox="0 0 560 {height}" width="100%" height="auto" role="img" '
           f'xmlns="http://www.w3.org/2000/svg">'
           f'<title>The model cannot place an order</title>'
           f'<desc>The tool server the model talks to offers read-only tools. '
           f'There is no order-placing tool for it to call.</desc>']
    out.append(f'<rect x="14" y="76" width="150" height="48" rx="6" fill="{PANEL}" stroke="{RULE}"/>')
    out.append(_t(89, 105, "THE MODEL", fill=CHALK, size=label_size, anchor="middle", ls=1.2))
    out.append(f'<line x1="164" y1="100" x2="206" y2="100" stroke="{SLATE}"/>' + _head(214, 100))
    out.append(f'<rect x="214" y="76" width="150" height="48" rx="6" fill="{PANEL}" stroke="{RULE}"/>')
    out.append(_t(289, 105, "THE TOOL SERVER", fill=CHALK, size=label_size, anchor="middle", ls=1.2))
    for i, tool in enumerate(tools or ["No tools called"]):
        y = 30 + 54 * i
        out.append(f'<rect x="430" y="{y}" width="116" height="34" rx="6" fill="{PANEL}" stroke="{RULE}"/>')
        out.append(_t(488, y + 22, tool, fill=CHALK, size=label_size - 1, weight="500",
                      anchor="middle"))
        out.append(f'<polyline points="364,100 400,{y + 17} 424,{y + 17}" fill="none" '
                   f'stroke="{SLATE}"/>' + _head(424, y + 17))
    gy = 30 + 54 * k + 18
    out.append(f'<rect x="430" y="{gy}" width="116" height="34" rx="6" fill="none" stroke="{TRACK}" '
               f'stroke-dasharray="3 3"/>')
    out.append(_t(488, gy + 22, "Place an order", fill=DIM, size=label_size - 1,
                  weight="500", anchor="middle"))
    out.append(f'<polyline points="364,100 392,{gy - 6}" fill="none" stroke="{TRACK}" '
               f'stroke-dasharray="2 4"/>')
    out.append(f'<circle cx="398" cy="{gy - 1}" r="4" fill="none" stroke="{OXIDE}"/>')
    out.append(_t(398, gy + 44, "NOTHING CONNECTS HERE", fill=OXIDE, size=10,
                  anchor="middle", ls=1.4))
    out.append("</svg>")
    return "".join(out)


def _pct(x) -> str:
    return f"{x:.0%}" if isinstance(x, float) else "—"


def equity_spark(S: dict, w: int = 470, h: int = 116) -> str:
    """The account since the agent's first decision. Drawn honestly: the scale
    starts where the money started, so a small loss looks like a small loss."""
    pts = [p for p in S.get("equity_series") or []
           if isinstance(p, dict) and isinstance(p.get("e"), (int, float))]
    if len(pts) < 2:
        return ""
    vals = [float(p["e"]) for p in pts]
    start = S.get("start_equity") or vals[0]
    lo, hi = min(vals + [start]), max(vals + [start])
    span = (hi - lo) or 1.0
    pad = span * 0.18
    lo, hi = lo - pad, hi + pad
    left, right, top, bot = 8, w - 96, 20, h - 30

    def sx(i):
        return left + (right - left) * i / (len(vals) - 1)

    def sy(v):
        return bot - (bot - top) * (v - lo) / (hi - lo)

    y0 = sy(start)
    line = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
    end_y = sy(vals[-1])
    return "".join([
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="auto" role="img" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<title>The account since the agent started</title>'
        f'<desc>It began at {start:,.0f} and stands at {vals[-1]:,.0f}.</desc>',
        # where the money started, as a reference the eye can measure against
        f'<line x1="{left}" y1="{y0:.1f}" x2="{right}" y2="{y0:.1f}" stroke="{RULE}" '
        f'stroke-dasharray="2 3" stroke-width="1" vector-effect="non-scaling-stroke"/>',
        _t(left, y0 - 7, f"started {start:,.0f}", fill=DIM, size=10, family=MONO,
           weight="400", ls=0.2),
        f'<polyline points="{line}" fill="none" stroke="{CHALK}" stroke-width="1.5" '
        f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/>',
        f'<rect x="{right - 2.5:.1f}" y="{end_y - 2.5:.1f}" width="5" height="5" fill="{CHALK}"/>',
        _t(right + 12, end_y + 4, f"{vals[-1]:,.2f}", fill=CHALK, size=13, family=MONO,
           weight="500"),
        _t(left, h - 8, "THE ACCOUNT SINCE IT STARTED", fill=DIM, size=10, ls=1.4),
        "</svg>",
    ])
