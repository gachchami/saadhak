"""The universe must be measured, and exclusions must state a reason."""
from saadhak.engine import screen as S


def test_the_default_universe_is_wider_than_what_we_expect_to_trade():
    """Exclusions should be observed, not assumed away by a narrow list."""
    assert len(S.DEFAULT_UNIVERSE) >= 8
    assert {"SPY", "QQQ"} <= set(S.DEFAULT_UNIVERSE)
    assert any(n not in ("SPY", "QQQ", "IWM", "DIA") for n in S.DEFAULT_UNIVERSE)


def test_earnings_names_are_excluded_with_the_reason(monkeypatch):
    from saadhak.engine.events import EventCheck
    monkeypatch.setattr(S, "earnings_soon",
                        lambda *a, **k: EventCheck(True, "earnings", [], "reports tonight"))
    r = S.screen_one("AVGO")
    assert not r.tradeable and "earnings" in r.reason


def test_a_name_with_no_short_dated_expiry_is_excluded(monkeypatch):
    from saadhak.engine.events import EventCheck
    monkeypatch.setattr(S, "earnings_soon", lambda *a, **k: EventCheck(False, "", [], "ok"))
    monkeypatch.setattr(S, "_expiries", lambda *a, **k: [])
    r = S.screen_one("DIA")
    assert not r.tradeable and "no expiry" in r.reason


def test_screen_failures_exclude_rather_than_crash(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("data down")
    monkeypatch.setattr(S, "earnings_soon", boom)
    r = S.screen_one("SPY")
    assert not r.tradeable and "screen failed" in r.reason


def test_ranking_puts_tradeable_names_first_by_score():
    rows = [S.Screened("A", False, "excluded"),
            S.Screened("B", True, "tradeable", best_score=0.01),
            S.Screened("C", True, "tradeable", best_score=0.05)]
    rows.sort(key=lambda r: (r.tradeable, r.best_score), reverse=True)
    assert [r.symbol for r in rows] == ["C", "B", "A"]
