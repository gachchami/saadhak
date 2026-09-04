"""Idle-time study, and the reason the task is fixed rather than chosen."""
from datetime import date

from saadhak.practitioner import study as S
from saadhak.witness.calibration import Calibration, Resolved


def test_feedback_names_overconfidence(monkeypatch):
    rows = [Resolved("SPY", date(2026, 8, 1), 1, 2, 0.9, 1.5, i < 5) for i in range(10)]
    monkeypatch.setattr(S, "calibration_now", lambda **k: Calibration(
        brier=0.4, n=10, resolved=rows, mean_p=0.9, hit_rate=0.5))
    note = S.feedback_note()
    assert "OVERCONFIDENT" in note and "Widen" in note


def test_feedback_names_underconfidence(monkeypatch):
    rows = [Resolved("SPY", date(2026, 8, 1), 1, 2, 0.6, 1.5, True) for _ in range(10)]
    monkeypatch.setattr(S, "calibration_now", lambda **k: Calibration(
        brier=0.16, n=10, resolved=rows, mean_p=0.6, hit_rate=0.95))
    note = S.feedback_note()
    assert "UNDERCONFIDENT" in note


def test_feedback_survives_an_empty_record(monkeypatch):
    monkeypatch.setattr(S, "calibration_now", lambda **k: Calibration(None, 0, []))
    assert "no scored record" in S.feedback_note()


def test_targets_are_never_repeated():
    scored = {("SPY", "2026-08-20")}
    import saadhak.practitioner.practice as P
    original = P.trading_days_back
    P.trading_days_back = lambda s, n: [date(2026, 8, 20)]
    try:
        assert S.pick_target(["SPY"], scored) is None
    finally:
        P.trading_days_back = original


def test_only_the_fixed_band_task_is_scored():
    """A forecaster that picks its own range widens it until it cannot miss.
    Mixing that with the fixed-band task produces a score describing neither."""
    import inspect

    from saadhak.witness import calibration
    src = inspect.getsource(calibration.current)
    assert 'task") == "fixed_band"' in src
