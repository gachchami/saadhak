import pytest

from saadhak.engine.sizing import calibration_multiplier, size_structure


@pytest.mark.parametrize("brier,expected", [
    (0.05, 1.00),   # better than needed, clipped at full size
    (0.10, 1.00),   # calibrated
    (0.25, 0.70),   # coin flip
    (0.40, 0.40),
    (0.60, 0.25),   # clipped at the floor
    (None, 0.60),   # prior, before any resolved forecasts
])
def test_calibration_multiplier(brier, expected):
    assert calibration_multiplier(brier) == pytest.approx(expected, abs=1e-9)


def test_size_scales_with_calibration(condor):
    """A calibrated model earns size. A badly calibrated one cannot afford a single
    contract at the 1.5% cap, so the discipline stops trading on its theses entirely."""
    good, _ = size_structure(condor, 100_000, brier=0.10)
    poor, _ = size_structure(condor, 100_000, brier=0.50)
    assert good == 3
    assert poor == 0


def test_size_respects_the_per_structure_cap(condor):
    qty, why = size_structure(condor, 100_000, brier=0.10)
    assert qty * condor.max_loss_per_unit <= why["budget"]
    assert qty * condor.max_loss_per_unit <= 100_000 * 0.015


def test_no_portfolio_headroom_means_no_trade(condor):
    qty, why = size_structure(condor, 100_000, brier=0.10, open_risk=6_000)
    assert qty == 0
    assert "headroom" in why["reason"]
