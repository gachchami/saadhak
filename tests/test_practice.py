"""Practice is only honest if the model cannot see the answer."""
from datetime import date

from saadhak.practitioner import practice


def test_history_stops_strictly_before_the_target(monkeypatch):
    target = date(2026, 8, 20)
    served = {}

    def fake_bars(symbol, start, end):
        served["end"] = end
        return [{"t": f"2026-08-{d:02d}T00:00:00Z", "o": 100, "h": 101,
                 "l": 99, "c": 100 + d} for d in range(1, 20)]

    monkeypatch.setattr(practice, "_bars", fake_bars)
    monkeypatch.setattr(practice, "ask_json", lambda *a, **k: type(
        "R", (), {"ok": False, "parsed": None})())
    practice.one_round("SPY", target)
    assert served["end"] < target, "history window must end before the target day"


def test_bars_on_or_after_the_target_are_dropped(monkeypatch):
    target = date(2026, 8, 20)
    captured = {}

    def fake_bars(symbol, start, end):
        return [{"t": f"2026-08-{d:02d}T00:00:00Z", "o": 100, "h": 101,
                 "l": 99, "c": 100.0 + d} for d in range(10, 25)]

    def fake_ask(system, user, **k):
        captured["prompt"] = user
        return type("R", (), {"ok": False, "parsed": None})()

    monkeypatch.setattr(practice, "_bars", fake_bars)
    monkeypatch.setattr(practice, "ask_json", fake_ask)
    practice.one_round("SPY", target)
    for d in range(20, 25):
        assert f"2026-08-{d}" not in captured["prompt"], f"leaked bar for {d}"


def test_scoring_matches_the_brier_definition():
    r = practice.PracticeRound("SPY", date(2026, 8, 20), 100, 110, 0.9, 105, True)
    assert r.brier_contribution < 0.011
    wrong = practice.PracticeRound("SPY", date(2026, 8, 20), 100, 110, 0.9, 120, False)
    assert wrong.brier_contribution > 0.8
