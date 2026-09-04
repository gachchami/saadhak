"""Gate 8 must follow from the exit rules, not from a guessed percentage."""
import pytest

from saadhak.engine.expectancy import evaluate, win_probability
from tests.conftest import mk_contract


def leg_with(condor, index, **kw):
    c = mk_contract(**kw)
    condor.legs[index] = type(condor.legs[index])(c, condor.legs[index].side,
                                                  condor.legs[index].position_intent)
    return condor


def test_breakeven_follows_from_tp_and_sl(condor):
    """TP at 50% of credit and a stop at 2x means we must win 2 times in 3."""
    e = evaluate(condor)
    assert e.breakeven_prob == pytest.approx(2 / 3, abs=1e-9)


def test_ten_delta_condor_is_accepted(condor):
    e = evaluate(condor)
    assert e.ok, e.reason
    assert e.win_prob == pytest.approx(0.81, abs=1e-6)   # 0.9 * 0.9
    assert e.ev_per_contract > 0


def test_twenty_delta_condor_is_refused_despite_a_fat_credit(condor):
    """A richer credit does not rescue a structure that loses too often.
    This is the case the old percentage-of-width floor waved through."""
    condor = leg_with(condor, 0, symbol="SPY..P00755000", kind="put", strike=755.0,
                      bid=1.80, ask=1.82, delta=-0.20)
    condor = leg_with(condor, 2, symbol="SPY..C00770000", kind="call", strike=770.0,
                      bid=1.78, ask=1.80, delta=0.20)
    e = evaluate(condor)
    assert e.win_prob == pytest.approx(0.64, abs=1e-6)
    assert not e.ok and "below breakeven" in e.reason
    assert e.ev_per_contract < 0


def test_credit_under_the_tick_is_refused(condor):
    condor = leg_with(condor, 0, symbol="SPY..P00750000", kind="put", strike=750.0,
                      bid=0.30, ask=0.31, delta=-0.10)
    condor = leg_with(condor, 2, symbol="SPY..C00775000", kind="call", strike=775.0,
                      bid=0.01, ask=0.02, delta=0.10)
    e = evaluate(condor)
    assert not e.ok


def test_credit_that_does_not_cover_the_spread_is_refused(condor):
    wide = dict(bid=0.50, ask=0.90)   # 0.40 spread on each short leg
    condor = leg_with(condor, 0, symbol="SPY..P00750000", kind="put", strike=750.0,
                      delta=-0.10, **wide)
    condor = leg_with(condor, 2, symbol="SPY..C00775000", kind="call", strike=775.0,
                      delta=0.10, **wide)
    e = evaluate(condor)
    assert not e.ok and "spread" in e.reason


def test_win_probability_multiplies_both_short_legs(condor):
    assert win_probability(condor) == pytest.approx(0.81, abs=1e-6)


def test_reservation_credit_is_the_binding_floor(condor):
    """The walk may spend the slack between the mid and this number, no more."""
    from saadhak.config import settings
    from saadhak.engine.expectancy import reservation_credit, spread_cost
    s = settings()
    r = reservation_credit(condor)
    assert r == round(max(s.min_credit_abs, spread_cost(condor) * s.spread_cover_multiple), 2)
    assert r <= condor.net_credit, "a structure that passed the gate must have slack"


def test_at_the_reservation_credit_the_structure_still_clears(condor):
    """One tick below it must fail, or the floor is in the wrong place."""
    from saadhak.engine.expectancy import evaluate, reservation_credit
    r = reservation_credit(condor)
    assert evaluate(condor).ok
    assert r >= 0.10


def test_a_structure_that_cannot_fill_is_refused(condor):
    """Five orders in one session were posted at a mid that no fill could reach.
    A trade whose marketable price is under its own floor does not exist."""
    from dataclasses import replace
    from saadhak.engine.expectancy import evaluate, natural_credit, reservation_credit
    assert evaluate(condor).ok
    # Widen every quote so the bid side collapses below the reservation credit.
    wide = replace(condor, legs=[
        replace(l, contract=replace(l.contract, bid=max(l.contract.bid - 0.40, 0.01),
                                    ask=l.contract.ask + 0.40))
        for l in condor.legs])
    e = evaluate(wide)
    assert not e.ok
    assert "unfillable" in e.reason or "spread cost" in e.reason, e.reason


def test_natural_credit_is_the_marketable_price(condor):
    from saadhak.engine.expectancy import natural_credit
    expected = sum((l.contract.bid if l.side == "sell" else -l.contract.ask) * l.ratio_qty
                   for l in condor.legs)
    assert natural_credit(condor) == round(expected, 2)
    assert natural_credit(condor) <= condor.net_credit, "natural must be worse than the mid"
