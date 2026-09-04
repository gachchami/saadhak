import pytest

from saadhak.engine import gates as G
from saadhak.engine.monitor import attach_exit_rules
from tests.conftest import mk_contract


def ctx_for(condor, **kw):
    attach_exit_rules(condor)
    base = dict(structure=condor, equity=100_000, qty=1, market_open=True,
                minutes_since_open=60, minutes_to_close=120, spot=762.0,
                whitelist=["SPY", "QQQ"])
    base.update(kw)
    return G.GateContext(**base)


def test_a_good_condor_passes_every_gate(condor):
    results = G.evaluate(ctx_for(condor))
    assert G.passed(results), [str(r) for r in G.failures(results)]
    assert len(results) == 19


def test_first_and_last_fifteen_minutes_are_refused(condor):
    assert not G.passed(G.evaluate(ctx_for(condor, minutes_since_open=5)))
    assert not G.passed(G.evaluate(ctx_for(condor, minutes_to_close=5)))


def test_exits_are_exempt_from_the_time_window(condor):
    r = G.evaluate(ctx_for(condor, minutes_to_close=5, is_exit=True))
    assert [x for x in r if x.n == 1][0].ok


def test_daily_loss_halts_new_entries(condor):
    r = G.evaluate(ctx_for(condor, daily_pl_pct=-0.031))
    assert not [x for x in r if x.n == 6][0].ok


def test_gate_8_refuses_a_structure_that_loses_too_often(condor):
    """Gate 8 is expectancy, not a credit percentage: a fat credit on 20-delta
    strikes is refused because the exit rules need a 2-in-3 win rate."""
    rich_put = mk_contract("SPY..P00755000", "put", 755.0, bid=1.80, ask=1.82, delta=-0.20)
    rich_call = mk_contract("SPY..C00770000", "call", 770.0, bid=1.78, ask=1.80, delta=0.20)
    condor.legs[0] = type(condor.legs[0])(rich_put, "sell", "sell_to_open")
    condor.legs[2] = type(condor.legs[2])(rich_call, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    g8 = [x for x in r if x.n == 8][0]
    assert not g8.ok and "breakeven" in g8.reason


def test_a_short_strike_too_close_to_the_money_is_refused_by_expectancy(condor):
    """Gate 9 no longer polices delta with a hand-picked band; gate 8 refuses
    this structure because it does not win often enough to clear breakeven."""
    fat = mk_contract("SPY..P00750000", "put", 750.0, bid=0.60, ask=0.62, delta=-0.35)
    condor.legs[0] = type(condor.legs[0])(fat, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    assert [x for x in r if x.n == 9][0].ok, "deltas are present, so the data gate passes"
    assert not [x for x in r if x.n == 8][0].ok, "expectancy must refuse it"


def test_a_very_far_out_of_the_money_short_is_no_longer_refused(condor):
    """The old 0.08 floor rejected the highest-probability structures, which is
    what the search kept choosing. Only credit adequacy should stop these."""
    far = mk_contract("SPY..P00740000", "put", 740.0, bid=0.80, ask=0.82, delta=-0.04)
    condor.legs[0] = type(condor.legs[0])(far, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    assert [x for x in r if x.n == 9][0].ok


def test_gate_9_refuses_a_structure_whose_deltas_are_unknown(condor):
    blind = mk_contract("SPY..P00750000", "put", 750.0, bid=0.85, ask=0.87, delta=None)
    condor.legs[0] = type(condor.legs[0])(blind, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    g9 = [x for x in r if x.n == 9][0]
    assert not g9.ok and "missing" in g9.reason


def test_illiquid_leg_is_refused(condor):
    dead = mk_contract("SPY..P00750000", "put", 750.0, bid=0.0, ask=0.62, delta=-0.10)
    condor.legs[0] = type(condor.legs[0])(dead, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    assert not [x for x in r if x.n == 7][0].ok


def test_client_order_id_is_deterministic(condor):
    a = G.client_order_id(condor, "cycle-1")
    b = G.client_order_id(condor, "cycle-1")
    c = G.client_order_id(condor, "cycle-2")
    assert a == b and a != c and len(a) == 32


def test_a_long_wing_with_no_bid_is_still_tradeable(condor):
    """The far wing is bought at the ask and often has no bid at all. Demanding
    one refused executable condors; found by the threshold audit, not by hand."""
    wing = mk_contract("SPY..C00780000", "call", 780.0, bid=0.0, ask=0.03, delta=0.02)
    condor.legs[3] = type(condor.legs[3])(wing, "buy", "buy_to_open")
    r = G.evaluate(ctx_for(condor))
    assert [x for x in r if x.n == 7][0].ok


def test_a_short_leg_with_no_bid_is_still_refused(condor):
    """We sell into the bid, so a short leg without one cannot be opened."""
    dead = mk_contract("SPY..P00750000", "put", 750.0, bid=0.0, ask=0.87, delta=-0.10)
    condor.legs[0] = type(condor.legs[0])(dead, "sell", "sell_to_open")
    r = G.evaluate(ctx_for(condor))
    g7 = [x for x in r if x.n == 7][0]
    assert not g7.ok and "no bid to sell into" in g7.reason


def test_a_long_leg_with_no_ask_is_refused(condor):
    nothing = mk_contract("SPY..C00780000", "call", 780.0, bid=0.0, ask=0.0, delta=0.02)
    condor.legs[3] = type(condor.legs[3])(nothing, "buy", "buy_to_open")
    r = G.evaluate(ctx_for(condor))
    g7 = [x for x in r if x.n == 7][0]
    assert not g7.ok and "no ask to buy" in g7.reason
