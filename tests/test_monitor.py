from saadhak.engine.monitor import attach_exit_rules, check_exit


def test_take_profit_at_half_the_credit(condor):
    attach_exit_rules(condor)                 # credit 1.14 -> TP 0.57, SL 2.28
    d = check_exit(condor, current_cost=0.28, spot=762.0, minutes_to_close=120)
    assert d.should_exit and d.rule == "tp_50pct"


def test_stop_at_twice_the_credit(condor):
    attach_exit_rules(condor)
    d = check_exit(condor, current_cost=2.30, spot=762.0, minutes_to_close=120)
    assert d.should_exit and d.rule == "sl_2x"


def test_holds_in_between(condor):
    attach_exit_rules(condor)
    d = check_exit(condor, current_cost=1.00, spot=762.0, minutes_to_close=120)
    assert not d.should_exit


def test_time_stop_near_the_close(condor):
    attach_exit_rules(condor)
    d = check_exit(condor, current_cost=1.00, spot=762.0, minutes_to_close=10)
    assert d.should_exit and d.rule == "time_stop"


def test_proximity_close_when_a_short_strike_is_pinned(condor):
    attach_exit_rules(condor)
    d = check_exit(condor, current_cost=1.00, spot=750.5, minutes_to_close=25)
    assert d.should_exit and d.rule == "proximity"


# --- the time stop must not throw away a winning expiry ---------------------
from dataclasses import dataclass
from datetime import UTC, date, datetime

from saadhak.loop import exit_check
from saadhak.witness.positions import OpenLeg, OpenStructure


def _condor(spot_legs, expiry=None):
    # The engine compares expiry against the UTC date, so the test must too:
    # in IST the local date is already tomorrow while the US session is today.
    expiry = expiry or datetime.now(UTC).date()
    legs = [OpenLeg(symbol=f"SPY..{k}", qty=q, avg_entry_price=e, current_price=c,
                    market_value=mv, strike=k, kind=kind, expiry=expiry)
            for k, q, e, c, mv, kind in spot_legs]
    return OpenStructure("SPY", expiry, legs)


def _safe_condor():
    # short 755P / long 754P, short 770C / long 771C, 11x, credit 0.15
    return _condor([
        (755.0, -11, 0.33, 0.115, -126.5, "put"),
        (754.0, 11, 0.27, 0.075, 82.5, "put"),
        (770.0, -11, 0.28, 0.375, -412.5, "call"),
        (771.0, 11, 0.19, 0.195, 214.5, "call"),
    ])


def test_time_stop_holds_when_shorts_are_clear():
    """The whole credit is kept by letting a safe spread expire. Closing it
    pays the spread to give that up."""
    st = _safe_condor()
    should, rule, detail = exit_check(st, spot=765.44, minutes_to_close=10)
    assert not should
    assert rule == "expire_worthless"
    assert "keeps the full" in detail


def test_time_stop_closes_when_a_short_is_threatened():
    st = _safe_condor()
    should, rule, detail = exit_check(st, spot=768.5, minutes_to_close=10)
    assert should and rule == "time_stop"
    assert "770C" in detail


def test_time_stop_closes_when_a_short_is_already_in_the_money():
    st = _safe_condor()
    should, rule, _ = exit_check(st, spot=770.5, minutes_to_close=10)
    assert should and rule == "time_stop"


# --- unfilled orders must not linger ---------------------------------------

def test_a_stale_order_is_cancelled(monkeypatch):
    """One sat open for ninety minutes because the limit walk was never called.
    It can fill later, at a price the decision was not made at."""
    from datetime import UTC, datetime, timedelta

    from saadhak import loop as L

    old = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    monkeypatch.setattr(L, "open_orders", lambda: [
        {"id": "abc12345", "submitted_at": old, "limit_price": "-0.19"}])
    cancelled = []
    monkeypatch.setattr(L, "cancel", lambda i: cancelled.append(i))
    monkeypatch.setattr(L.journal, "append", lambda *a, **k: None)
    assert L.sweep_stale_orders(max_age_min=5, verbose=False) == ["abc12345"]
    assert cancelled == ["abc12345"]


def test_a_fresh_order_is_left_alone(monkeypatch):
    from datetime import UTC, datetime, timedelta

    from saadhak import loop as L

    fresh = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    monkeypatch.setattr(L, "open_orders", lambda: [
        {"id": "abc", "submitted_at": fresh, "limit_price": "-0.19"}])
    monkeypatch.setattr(L, "cancel", lambda i: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(L.journal, "append", lambda *a, **k: None)
    assert L.sweep_stale_orders(max_age_min=5, verbose=False) == []
