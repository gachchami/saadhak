"""Idle-hours study: the desk gets better at knowing what it knows.

The options market is open six and a half hours in twenty-four, so the agent
spends roughly three quarters of its life waiting. Waiting is free; being
unmeasured is not. During the closed hours the practitioner forecasts sessions
that have already happened and is scored on them, which grows the evidence behind
its position sizing without risking a cent.

The part that makes this improvement rather than accumulation is the feedback.
Each round is shown its own record so far -- what it has been claiming, how often
it has actually been right, and the forecasts it got worst -- so a systematic
lean has something to correct against. A model told it has been underconfident by
seven points can widen or narrow accordingly; a model told nothing can only
repeat itself.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from saadhak.config import settings
from saadhak.practitioner import practice
from saadhak.practitioner.llm import BUDGET, cooling_down
from saadhak.witness import journal
from saadhak.witness.calibration import current as calibration_now

STUDY_SYMBOLS = ("SPY", "QQQ", "IWM", "GLD", "SMH", "DIA", "XLF", "XLE", "EEM", "TLT")


@dataclass
class StudyResult:
    attempted: int = 0
    scored: int = 0
    skipped: int = 0
    brier_before: float | None = None
    brier_after: float | None = None
    n_before: int = 0
    n_after: int = 0

    @property
    def improved(self) -> bool | None:
        if self.brier_before is None or self.brier_after is None:
            return None
        return self.brier_after < self.brier_before

    @property
    def summary(self) -> str:
        if not self.scored:
            return f"no new forecasts ({self.skipped} already scored)"
        move = ""
        if self.brier_before is not None and self.brier_after is not None:
            d = self.brier_after - self.brier_before
            move = f", Brier {self.brier_before:.3f} -> {self.brier_after:.3f} ({d:+.3f})"
        return f"scored {self.scored} of {self.attempted}, n={self.n_after}{move}"


def already_scored() -> set[tuple[str, str]]:
    return {(r["data"].get("symbol"), r["data"].get("expiry"))
            for r in practice._all_records_safe()
            if r.get("type") == "forecast_resolved"}


def feedback_note() -> str:
    """What the desk knows about its own record, phrased for the forecaster."""
    cal = calibration_now(resolve=False)
    if not cal.n or cal.mean_p is None:
        return ("You have no scored record yet. State probabilities you would "
                "defend rather than ones that sound confident.")
    gap = cal.mean_p - (cal.hit_rate or 0.0)
    if gap > 0.05:
        lean = (f"You have been OVERCONFIDENT: you claim {cal.mean_p:.0%} but are "
                f"right {cal.hit_rate:.0%} of the time. Widen your ranges, or lower "
                f"your stated probability for the same range.")
    elif gap < -0.05:
        lean = (f"You have been UNDERCONFIDENT: you claim {cal.mean_p:.0%} but are "
                f"right {cal.hit_rate:.0%} of the time. You are leaving accuracy "
                f"unclaimed; narrow your ranges, or raise your probability.")
    else:
        lean = (f"You are well calibrated: claiming {cal.mean_p:.0%} and right "
                f"{cal.hit_rate:.0%}. Hold this standard.")

    sharp = ""
    if cal.resolved:
        widths = [(r.hi - r.lo) / r.close for r in cal.resolved if r.close]
        if widths:
            sharp = (f" Average band width {sum(widths) / len(widths):.1%} of price.")
    worst = sorted(cal.resolved, key=lambda r: r.brier_contribution, reverse=True)[:3]
    misses = "\n".join(
        f"  {r.symbol} {r.expiry}: you said {r.p:.0%} for {r.lo:g}-{r.hi:g}, "
        f"it closed {r.close:.2f} ({'inside' if r.inside else 'OUTSIDE'})"
        for r in worst)
    return (f"Your record so far: Brier {cal.brier:.3f} over {cal.n} forecasts."
            f"{sharp} {lean}\n\nYour worst forecasts:\n{misses}")


def pick_target(symbols: list[str], scored: set[tuple[str, str]],
                lookback: int = 25) -> tuple[str, date] | None:
    """An unscored (symbol, session) pair, preferring variety over recency."""
    order = list(symbols)
    random.shuffle(order)
    for symbol in order:
        try:
            days = practice.trading_days_back(symbol, lookback)
        except Exception:
            continue
        fresh = [d for d in days if (symbol, d.isoformat()) not in scored]
        if fresh:
            return symbol, random.choice(fresh)
    return None


def study_round(symbols: list[str] | None = None, *, band: float = 0.9) -> StudyResult:
    """One study round: forecast an unseen past session, with feedback attached."""
    s = settings()
    res = StudyResult()
    if not s.llm_enabled or BUDGET.exhausted:
        return res
    if cooling_down() > 0:
        res.skipped = 1          # nothing is urgent here; try again next cycle
        return res

    cal_before = calibration_now(resolve=False)
    res.brier_before, res.n_before = cal_before.brier, cal_before.n

    scored = already_scored()
    target = pick_target(list(symbols or STUDY_SYMBOLS), scored)
    if not target:
        res.skipped = len(scored)
        return res

    symbol, day = target
    res.attempted = 1
    r = practice.one_round(symbol, day, cycle_id="study",
                           feedback=feedback_note(), band=band)
    if r:
        res.scored = 1
        journal.append("forecast_resolved", {
            "symbol": r.symbol, "expiry": r.target.isoformat(), "lo": r.lo,
            "hi": r.hi, "p": r.p, "close": r.close, "inside": r.inside,
            "source": "study", "task": "fixed_band", "reasoning": r.reasoning,
            "brier_contribution": round(r.brier_contribution, 5)})

    cal_after = calibration_now(resolve=False)
    res.brier_after, res.n_after = cal_after.brier, cal_after.n
    journal.append("study", {
        "symbol": symbol, "target": day.isoformat(), "scored": res.scored,
        "brier_before": res.brier_before, "brier_after": res.brier_after,
        "n": res.n_after, "budget_spent_usd": round(BUDGET.spent_usd, 6)})
    return res
