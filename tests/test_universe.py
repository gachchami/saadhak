"""The universe is discovered from the options market, not typed."""
from datetime import date

from saadhak.engine import universe as U


def test_cash_settled_index_options_are_excluded():
    """European, settle to a print rather than shares, so our assignment and
    proximity rules do not describe them."""
    assert {"SPX", "XSP", "NDX", "RUT", "VIX"} <= U.CASH_SETTLED


def test_leveraged_products_are_excluded():
    """Their options price a daily-rebalanced return, so delta means something
    else and the expectancy model does not hold."""
    assert {"TQQQ", "SQQQ", "SOXL", "NUGT", "UVXY"} <= U.LEVERAGED


def test_discovery_counts_and_excludes(monkeypatch):
    pages = [{"option_contracts": [
        {"underlying_symbol": "SPY"}, {"underlying_symbol": "SPY"},
        {"underlying_symbol": "SPX"},          # cash settled
        {"underlying_symbol": "TQQQ"},         # leveraged
        {"underlying_symbol": "MU"},
    ]}]
    monkeypatch.setattr(U, "trading", lambda *a, **k: pages[0])
    d = U.discover(date(2026, 9, 4), use_cache=False)
    assert d.counts["SPY"] == 2 and d.counts["MU"] == 1
    assert "SPX" not in d.counts and "TQQQ" not in d.counts
    assert d.excluded["SPX"] == "cash-settled index option"
    assert d.excluded["TQQQ"] == "leveraged or inverse product"


def test_ranking_is_by_contracts_listed(monkeypatch):
    monkeypatch.setattr(U, "trading", lambda *a, **k: {"option_contracts":
        [{"underlying_symbol": "A"}] * 5 + [{"underlying_symbol": "B"}] * 9})
    d = U.discover(date(2026, 9, 4), use_cache=False)
    assert d.top(2) == ["B", "A"]


def test_a_symbol_matching_a_leverage_hint_is_excluded(monkeypatch):
    monkeypatch.setattr(U, "trading", lambda *a, **k: {"option_contracts":
        [{"underlying_symbol": "FNGU3X"}, {"underlying_symbol": "SPY"}]})
    d = U.discover(date(2026, 9, 4), use_cache=False)
    assert "FNGU3X" not in d.counts and d.counts["SPY"] == 1


def test_the_screen_falls_back_when_discovery_fails(monkeypatch):
    from saadhak.engine import screen as S
    assert len(S.FALLBACK_UNIVERSE) >= 8
    assert "SPY" in S.FALLBACK_UNIVERSE


# --- expired contracts must not be screened --------------------------------

def test_todays_expiry_is_live_during_the_session():
    from datetime import UTC, datetime
    today = datetime.now(UTC).date()
    assert U.live_expiries([today], market_open=True) == [today]


def test_todays_expiry_is_dead_after_the_close():
    """It settled at 16:00. Quoting it afterwards reads terminal prices as a market."""
    from datetime import UTC, datetime
    today = datetime.now(UTC).date()
    assert U.live_expiries([today], market_open=False) == []


def test_past_expiries_are_always_dropped():
    from datetime import UTC, datetime, timedelta
    today = datetime.now(UTC).date()
    old = today - timedelta(days=3)
    assert old not in U.live_expiries([old, today], market_open=True)


def test_future_expiries_survive_either_way():
    from datetime import UTC, datetime, timedelta
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    assert U.live_expiries([tomorrow], market_open=False) == [tomorrow]
    assert U.live_expiries([tomorrow], market_open=True) == [tomorrow]
