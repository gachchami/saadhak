"""Three condors sold into one rally, three stops. Nothing malfunctioned; nothing
noticed either."""
from saadhak.engine import regime as R


def _exits(monkeypatch, rows):
    monkeypatch.setattr(R, "_exits_today", lambda: rows)


def test_two_consecutive_stops_on_a_symbol_stop_new_entries(monkeypatch):
    _exits(monkeypatch, [
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -242},
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -273},
    ])
    c = R.check("SPY")
    assert c.blocked and "consecutive stops" in c.reason


def test_a_win_between_stops_breaks_the_run(monkeypatch):
    _exits(monkeypatch, [
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -242},
        {"structure": "SPY condor", "rule": "tp_50pct", "pl": 82},
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -273},
    ])
    assert not R.check("SPY").blocked


def test_another_symbol_is_judged_separately(monkeypatch):
    _exits(monkeypatch, [
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -242},
        {"structure": "SPY condor", "rule": "sl_2x", "pl": -273},
    ])
    assert R.check("SPY").blocked
    assert not R.check("QQQ").blocked


def test_enough_stops_across_the_desk_stop_everything(monkeypatch):
    _exits(monkeypatch, [{"structure": f"{s} condor", "rule": "sl_2x", "pl": -200}
                         for s in ("SPY", "QQQ", "IWM", "GLD")])
    c = R.check("META")
    assert c.blocked and "across the desk" in c.reason


def test_a_soft_brake_sits_in_front_of_the_hard_halt(monkeypatch):
    """The 3% daily halt is far past where a losing hypothesis should stop
    compounding."""
    _exits(monkeypatch, [{"structure": "SPY c", "rule": "tp_50pct", "pl": -1600}])
    c = R.check("SPY", equity=100_000)
    assert c.blocked and "soft brake" in c.reason


def test_a_quiet_day_is_not_blocked(monkeypatch):
    _exits(monkeypatch, [{"structure": "SPY condor", "rule": "tp_50pct", "pl": 82}])
    assert not R.check("SPY").blocked
