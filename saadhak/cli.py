"""saadhak — command line. status | plan | run | report | verify | kill"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table

from saadhak.broker import account as acct
from saadhak.broker.data import chain, latest_price, nearest_expiry
from saadhak.broker.orders import submit
from saadhak.config import settings
from saadhak.engine import gates as G
from saadhak.engine.monitor import attach_exit_rules
from saadhak.engine.sizing import size_structure
from saadhak.engine.decide import decide
from saadhak.loop import monitor_once, run_monitor
from saadhak import agent as agent_mod
from saadhak.engine.structures import build_credit_spread, build_iron_condor
from saadhak.witness import journal

app = typer.Typer(add_completion=False, help="Saadhak — the calibrated options agent.")
con = Console()


@app.command()
def status() -> None:
    """Account, clock, and a slice of the chain with deltas."""
    s = settings()
    a = acct.get_account()
    c = acct.get_clock()

    t = Table(title="Account", show_header=False, box=None)
    t.add_row("account", f"{a.account_number}  [dim]{a.id}[/dim]")
    t.add_row("equity", f"${a.equity:,.2f}")
    t.add_row("daily P/L", f"${a.daily_pl:+,.2f}  ({a.daily_pl_pct:+.2%})")
    t.add_row("options level", str(a.options_level))
    t.add_row("options BP", f"${a.options_buying_power:,.2f}")
    t.add_row("market", "[green]OPEN[/green]" if c["is_open"] else f"closed, opens {c['next_open']}")
    con.print(t)

    pos = acct.option_positions()
    con.print(f"\n[bold]Open option positions:[/bold] {len(pos)}")
    for p in pos:
        con.print(f"  {p['symbol']}  qty {p['qty']}  P/L ${float(p['unrealized_pl']):+,.2f}")

    for sym in s.symbols[:1]:
        exp = nearest_expiry(sym, s.max_dte)
        if not exp:
            continue
        spot = latest_price(sym)
        cs = chain(sym, exp, spot=spot)
        con.print(f"\n[bold]{sym}[/bold] spot ${spot:,.2f}  expiry {exp}  ({len(cs)} contracts)")
        tb = Table(box=None)
        for col in ("contract", "type", "strike", "delta", "bid", "ask", "vol", "greeks"):
            tb.add_column(col)
        near = sorted([c for c in cs if c.delta is not None],
                      key=lambda c: abs(c.abs_delta - 0.10))[:6]
        for c in sorted(near, key=lambda c: c.strike):
            tb.add_row(c.symbol, c.kind, f"{c.strike:g}", f"{c.delta:+.3f}",
                       f"{c.bid:.2f}", f"{c.ask:.2f}", str(c.volume), c.greeks_source)
        con.print(tb)


@app.command()
def plan(symbol: str = typer.Option("SPY", "--symbol", "-s"), book: str = "A") -> None:
    """Search the surface, pick the best structure, run every gate. Sends nothing."""
    d = decide(symbol, book=book)
    _render(d)


@app.command()
def run(dry_run: bool = typer.Option(True, "--dry-run/--live"),
        symbol: str = typer.Option("SPY", "--symbol", "-s"), book: str = "A") -> None:
    """One full cycle: search, gate, and (unless dry-run) submit."""
    d = decide(symbol, book=book)
    _render(d)
    if not d.accepted or not d.structure:
        return
    res = submit(d.structure, dry_run=dry_run, cycle_id=d.cycle_id)
    journal.append("order_submitted", {
        "cycle_id": d.cycle_id, "dry_run": dry_run, "body": res.body,
        "status": res.status, "order_id": res.order_id, "error": res.error})
    con.print(f"\n[bold]{res.status.upper()}[/bold] {d.structure.describe()}")
    if res.order_id:
        con.print(f"  order {res.order_id}")
    if res.error:
        con.print(f"  [red]{res.error}[/red]")


def _render(d) -> None:
    from saadhak.broker.provenance import capture as _prov
    _p = _prov()
    con.print(f"[dim]data: {_p.note}[/dim]")
    con.print(f"\n[bold]{d.symbol}[/bold] spot ${d.spot:,.2f}  "
              f"[dim]searched {d.search.considered} combinations, "
              f"{len(d.search.viable)} viable[/dim]")
    tb = Table(box=None, title="Top of the surface", title_justify="left")
    for c in ("expiry", "delta", "width", "credit", "P(win)", "EV/ct", "risk", "score"):
        tb.add_column(c, justify="right")
    for c in d.search.viable[:5]:
        r = c.row()
        tb.add_row(r["expiry"], f"{r['delta_target']:.2f}", f"{r['width']:.0f}",
                   f"{r['credit']:.2f}", f"{r['win_prob']:.0%}",
                   f"{r['ev_per_contract']:+.3f}", f"${r['max_loss_per_unit']:,.0f}",
                   f"{r['score']:.4f}")
    con.print(tb)
    if not d.structure:
        con.print(f"[yellow]REFUSE[/yellow]: {d.reason}")
        return
    st = d.structure
    con.print(f"\n[bold]chosen:[/bold] {st.describe()}")
    con.print(f"  credit ${st.net_credit:.2f} | risk ${st.max_loss_per_unit:,.0f}/unit "
              f"| total ${st.max_loss:,.0f} | qty {d.qty} "
              f"(multiplier {d.sizing.get('multiplier')})")
    con.print(f"  exits: TP ${st.meta['tp_price']:.2f} | SL ${st.meta['sl_price']:.2f} "
              f"| time stop 15m to close")
    if d.sizing.get("calibration"):
        con.print(f"  calibration: {d.sizing['calibration']}")
    con.print("\n[bold]Gates[/bold]")
    for r in d.gates:
        mark = "[green]PASS[/green]" if r.ok else "[red]FAIL[/red]"
        con.print(f"  {mark} {r.n:02d} {r.name:<16} {r.reason}")
    if d.verdict is not None and d.verdict.consulted:
        v = d.verdict
        con.print(f"\n[bold]Practitioner[/bold] ({v.model}, via MCP: "
                  f"{', '.join(v.tools_called)})")
        con.print(f"  verdict  {v.summary}")
        con.print(f"  thesis   {v.thesis}")
        if v.micro_forecast:
            con.print(f"  forecast {v.micro_forecast}")
    con.print(f"\n[bold]{'ACCEPT' if d.accepted else 'REFUSE'}[/bold]: {d.reason}")


@app.command()
def agent(dry_run: bool = typer.Option(False, "--dry-run/--live"),
          interval: int = typer.Option(60, "--interval"),
          symbols: str = typer.Option(None, "--symbols",
                                      help="pin the universe; omit to let the screen choose"),
          universe: str = typer.Option(None, "--universe",
                                       help="candidates the screen ranks"),
          top: int = typer.Option(3, "--top")) -> None:
    """Run autonomously: screen, open at entry windows, manage exits, halt on limits."""
    syms = [x.strip().upper() for x in symbols.split(",")] if symbols else None
    univ = [x.strip().upper() for x in universe.split(",")] if universe else None
    agent_mod.run(dry_run=dry_run, interval=interval, symbols=syms,
                  universe=univ, top=top)


@app.command()
def monitor(dry_run: bool = typer.Option(False, "--dry-run/--live"),
            interval: int = typer.Option(60, "--interval"),
            once: bool = typer.Option(False, "--once")) -> None:
    """Watch open structures and enforce the exit rules attached at entry."""
    if once:
        monitor_once(dry_run=dry_run)
    else:
        run_monitor(dry_run=dry_run, interval=interval)


@app.command()
def audit(symbols: str = typer.Option("SPY,QQQ,IWM", "--symbols"),
          per_symbol: int = typer.Option(12, "--per-symbol")) -> None:
    """Find thresholds that overrule the measurement, and constants that never fire."""
    from saadhak.engine.audit import run as _audit
    syms = [x.strip().upper() for x in symbols.split(",")]
    con.print(f"auditing gates against {per_symbol} top structures on "
              f"{', '.join(syms)}...\n")
    au = _audit(syms, per_symbol)
    tb = Table(box=None)
    for c in ("gate", "name", "kind", "refused", "over measurement", "verdict"):
        tb.add_column(c, justify="right")
    for n in sorted(au.stats):
        st = au.stats[n]
        colour = ("[red]" if st.refused_while_measured_passed else
                  "[yellow]" if st.verdict == "never fires — untested" else "")
        tb.add_row(f"{st.n:02d}", st.name, st.kind, str(st.refusals),
                   str(st.refused_while_measured_passed) if st.kind == "threshold" else "-",
                   f"{colour}{st.verdict}" + ("[/]" if colour else ""))
    con.print(tb)
    con.print(f"\n{au.considered} structures evaluated across {len(au.symbols)} symbols")
    if au.suspects:
        con.print("\n[bold red]Thresholds overruling the measurement[/bold red]")
        for st in au.suspects:
            con.print(f"  gate {st.n:02d} {st.name}: refused "
                      f"{st.refused_while_measured_passed} structures gate 08 approved; "
                      f"best score discarded {st.best_score_refused:.4f}")
            for ex in st.examples:
                con.print(f"    [dim]{ex}[/dim]")
    else:
        con.print("\n[green]no threshold is overruling the measurement[/green]")
    if au.untested:
        con.print("\n[yellow]Never fired — untested constants[/yellow]")
        for st in au.untested:
            con.print(f"  gate {st.n:02d} {st.name}")


@app.command()
def screen(universe: str = typer.Option(None, "--universe",
                                        help="override; omit to discover from the options market"),
           top: int = typer.Option(3, "--top"),
           shortlist: int = typer.Option(14, "--shortlist")) -> None:
    """Rank candidate underlyings by today's best expected value per dollar at risk."""
    from saadhak.engine.screen import screen as _screen
    names = [x.strip().upper() for x in universe.split(",")] if universe else None
    if names is None:
        from saadhak.engine.universe import candidates
        found, disc = candidates(top=shortlist)
        if disc:
            con.print(f"discovered {disc.total} underlyings listing options for "
                      f"{disc.expiry}, {len(disc.excluded)} excluded as cash-settled "
                      f"or leveraged; screening the top {len(found)}\n")
    con.print("" if names is None else f"screening {len(names)}: {', '.join(names)}\n")
    rows = _screen(names, top=top, shortlist=shortlist)
    tb = Table(box=None)
    for c in ("symbol", "spot", "expiries", "viable", "credit", "P(win)", "score", "verdict"):
        tb.add_column(c, justify="right")
    for r in rows:
        tb.add_row(r.symbol, f"{r.spot:,.2f}" if r.spot else "-",
                   str(len(r.expiries)), str(r.viable) if r.tradeable else "-",
                   f"{r.best_credit:.2f}" if r.tradeable else "-",
                   f"{r.best_win_prob:.0%}" if r.tradeable else "-",
                   f"{r.best_score:.4f}" if r.tradeable else "-",
                   "[green]trade[/green]" if r.tradeable else f"[dim]{r.reason[:46]}[/dim]")
    con.print(tb)
    chosen = [r.symbol for r in rows if r.tradeable][:top]
    con.print(f"\n[bold]chosen:[/bold] {', '.join(chosen) if chosen else 'none today'}")


@app.command()
def practice(sessions: int = typer.Option(8, "--sessions"),
             symbols: str = typer.Option("SPY,QQQ", "--symbols")) -> None:
    """Forecast recent sessions and score them, to earn a calibration before risking size."""
    from saadhak.engine.sizing import calibration_multiplier
    from saadhak.practitioner.practice import run
    syms = [x.strip().upper() for x in symbols.split(",")]
    con.print(f"practising on {sessions} sessions of {', '.join(syms)}...")
    rounds = run(syms, sessions)
    if not rounds:
        con.print("[red]no forecasts completed[/red]")
        raise typer.Exit(1)
    tb = Table(box=None)
    for c in ("symbol", "day", "range", "said", "close", "inside", "penalty"):
        tb.add_column(c, justify="right")
    for r in rounds:
        tb.add_row(r.symbol, r.target.isoformat(), f"{r.lo:g}-{r.hi:g}", f"{r.p:.0%}",
                   f"{r.close:.2f}", "[green]yes[/green]" if r.inside else "[red]no[/red]",
                   f"{r.brier_contribution:.3f}")
    con.print(tb)
    brier = sum(r.brier_contribution for r in rounds) / len(rounds)
    hit = sum(1 for r in rounds if r.inside) / len(rounds)
    said = sum(r.p for r in rounds) / len(rounds)
    con.print(f"\n[bold]Brier {brier:.3f}[/bold] over {len(rounds)} forecasts | "
              f"said {said:.0%}, right {hit:.0%} | "
              f"sizing multiplier {calibration_multiplier(brier):.2f}x")


@app.command()
def limiter() -> None:
    """Show the adaptive rate limiter's learned rate and circuit state."""
    from saadhak.practitioner.ratelimit import LIMITER
    st = LIMITER.status
    con.print(f"[bold]{st['state']}[/bold] · pacing {st['rate_per_min']}/min")
    con.print(f"allowed {st['allowed']} · refused locally {st['refused_locally']} · "
              f"throttled by provider {st['throttled_by_provider']}")


@app.command()
def study(rounds: int = typer.Option(5, "--rounds")) -> None:
    """Forecast unseen past sessions with feedback, to sharpen calibration."""
    from saadhak.engine.sizing import calibration_multiplier
    from saadhak.practitioner.study import study_round
    from saadhak.witness.calibration import current
    for i in range(rounds):
        r = study_round()
        con.print(f"  {i + 1}: {r.summary}")
    c = current(resolve=False)
    if c.brier is not None:
        con.print(f"\n[bold]{c.verdict}[/bold]")
        con.print(f"sizing multiplier {calibration_multiplier(c.brier):.2f}x")


@app.command()
def calibration() -> None:
    """Resolve outstanding forecasts and show the desk's measured calibration."""
    from saadhak.engine.sizing import calibration_multiplier
    from saadhak.witness.calibration import current
    c = current()
    con.print(f"[bold]{c.verdict}[/bold]")
    con.print(f"sizing multiplier: {calibration_multiplier(c.brier):.2f}x")
    if c.resolved:
        tb = Table(box=None)
        for col in ("symbol", "expiry", "range", "said", "close", "inside", "penalty"):
            tb.add_column(col, justify="right")
        for r in c.resolved[-10:]:
            tb.add_row(r.symbol, r.expiry.isoformat(), f"{r.lo:g}-{r.hi:g}",
                       f"{r.p:.0%}", f"{r.close:.2f}",
                       "[green]yes[/green]" if r.inside else "[red]no[/red]",
                       f"{r.brier_contribution:.3f}")
        con.print(tb)


@app.command()
def reconcile() -> None:
    """Compare broker state through the CLI against the engine's REST view."""
    from saadhak.witness.reconcile import reconcile as _r
    r = _r()
    con.print(("[green]" if r.ok else "[red]") + r.summary)


@app.command()
def publish() -> None:
    """Write state/latest.json for the dashboard."""
    from saadhak.witness.state import publish as _pub
    s = _pub()
    con.print(f"equity ${s['account']['equity']:,.2f} | "
              f"{len(s['open_structures'])} open | "
              f"{s['decisions']['total']} decisions | "
              f"calibration {s['calibration']['verdict']}")


@app.command()
def verify(day: str = typer.Option(None, "--day")) -> None:
    """Verify the journal hash chain."""
    ok, msg = journal.verify(day)
    con.print(("[green]" if ok else "[red]") + msg)


@app.command()
def report(day: str = typer.Option(None, "--day")) -> None:
    """Markdown summary of a day: P/L, decisions, refusals."""
    a = acct.get_account()
    recs = journal.read(day)
    gates = [r for r in recs if r["type"] == "gate_result"]
    orders = [r for r in recs if r["type"] == "order_submitted"]
    acc = [g for g in gates if g["data"].get("decision") == "accept"]
    ref = [g for g in gates if g["data"].get("decision") == "refuse"]
    con.print(f"## Saadhak — {day or datetime.now(UTC).date()}\n")
    con.print(f"- equity ${a.equity:,.2f}, daily P/L ${a.daily_pl:+,.2f} ({a.daily_pl_pct:+.2%})")
    con.print(f"- decisions: {len(gates)} ({len(acc)} accepted, {len(ref)} refused)")
    con.print(f"- orders: {len(orders)}")
    if ref:
        con.print("\n**Refusals**")
        for g in ref[-10:]:
            bad = [x for x in g["data"]["gates"] if not x["ok"]]
            con.print(f"- {g['data'].get('structure','?')} — " +
                      "; ".join(f"gate {b['n']:02d} {b['name']}: {b['reason']}" for b in bad))
    ok, msg = journal.verify(day)
    con.print(f"\n_journal: {msg}_")


if __name__ == "__main__":
    app()
