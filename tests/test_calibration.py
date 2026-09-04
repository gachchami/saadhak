import pytest

from datetime import date

from saadhak.engine.sizing import calibration_multiplier
from saadhak.witness.calibration import Calibration, Resolved


def r(p, inside, close=100.0):
    return Resolved("SPY", date(2026, 9, 1), 95.0, 105.0, p, close, inside)


def test_a_confident_and_correct_forecast_scores_near_zero():
    assert r(0.95, True).brier_contribution == pytest.approx(0.0025, abs=1e-9)


def test_confident_and_wrong_is_punished_hardest():
    assert r(0.95, False).brier_contribution > r(0.5, False).brier_contribution
    assert r(0.95, False).brier_contribution == pytest.approx(0.9025, abs=1e-9)


def test_saying_fifty_percent_scores_a_quarter_either_way():
    assert r(0.5, True).brier_contribution == pytest.approx(0.25, abs=1e-9)
    assert r(0.5, False).brier_contribution == pytest.approx(0.25, abs=1e-9)


def test_overconfidence_is_detected_and_named():
    rows = [r(0.9, True), r(0.9, False), r(0.9, False), r(0.9, True)]
    brier = sum(x.brier_contribution for x in rows) / len(rows)
    c = Calibration(brier=round(brier, 4), n=4, resolved=rows, mean_p=0.9, hit_rate=0.5)
    assert "overconfident" in c.verdict


def test_good_calibration_is_named():
    rows = [r(0.8, True)] * 4 + [r(0.8, False)]
    brier = sum(x.brier_contribution for x in rows) / len(rows)
    c = Calibration(brier=round(brier, 4), n=5, resolved=rows, mean_p=0.8, hit_rate=0.8)
    assert "well calibrated" in c.verdict


def test_the_score_actually_moves_position_size():
    """This is the whole claim: knowing what you know earns size."""
    calibrated = calibration_multiplier(0.10)
    coin_flip = calibration_multiplier(0.25)
    overconfident = calibration_multiplier(0.45)
    assert calibrated > coin_flip > overconfident
    assert calibrated == 1.0 and overconfident <= 0.35


def test_no_history_means_the_prior_not_full_size():
    c = Calibration(None, 0, [])
    assert "prior" in c.verdict
    assert calibration_multiplier(None) < 1.0
