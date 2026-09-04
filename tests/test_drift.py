"""Selling both sides at one delta assumes a symmetry the index does not have."""
from saadhak.engine.drift import Asymmetry


def _a(up, down):
    return Asymmetry("SPY", 617, 0.564, 0.192, up, down)


def test_the_call_side_is_pushed_further_out_when_it_breaches_more():
    a = _a(0.186, 0.135)            # measured on SPY
    assert a.ratio > 1.35
    assert a.call_delta(0.10) < 0.10
    assert a.put_delta(0.10) == 0.10


def test_a_symmetric_underlying_is_left_alone():
    a = _a(0.15, 0.15)
    assert a.call_delta(0.10) == 0.10 and a.put_delta(0.10) == 0.10


def test_a_downward_skew_pushes_the_put_side_out_instead():
    a = _a(0.10, 0.16)
    assert a.put_delta(0.10) < 0.10
    assert a.call_delta(0.10) == 0.10


def test_the_target_never_collapses_to_zero():
    a = _a(0.30, 0.001)
    assert a.call_delta(0.10) >= 0.02


def test_the_note_states_the_evidence():
    assert "breached" in _a(0.186, 0.135).note
