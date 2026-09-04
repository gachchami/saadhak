"""Our fallback greeks must match Alpaca's published values; 0DTE contracts have none."""
import pytest

from saadhak.greeks import greeks, implied_vol


# Alpaca snapshot, SPY 4-Sep-2026 760 put, spot 761.85, 2 DTE
ALPACA = {"delta": -0.4177, "gamma": 0.0407, "theta": -0.9047, "vega": 0.2202}


def test_matches_alpaca_greeks():
    g = greeks(761.85, 760.0, 2 / 365, 0.04, 0.1702, "put")
    for k, v in ALPACA.items():
        assert g[k] == pytest.approx(v, abs=0.01), f"{k}: {g[k]} vs {v}"


def test_implied_vol_round_trips():
    iv = implied_vol(2.93, 761.85, 760.0, 2 / 365, 0.04, "put")
    assert iv == pytest.approx(0.17, abs=0.02)


def test_far_otm_put_has_small_negative_delta():
    g = greeks(762.0, 700.0, 1 / 365, 0.04, 0.25, "put")
    assert -0.10 < g["delta"] <= 0.0


# --- spot must be on the same clock as the option quotes --------------------

def test_spot_falls_back_to_the_close_when_the_market_is_shut(monkeypatch):
    """Option quotes freeze at the close. Pairing them with an after-hours print
    misprices the straddle by the entire earnings move."""
    from datetime import UTC, datetime

    from saadhak.broker import data as D

    monkeypatch.setattr(D, "last_trade", lambda s: (368.00, datetime.now(UTC)))
    monkeypatch.setattr(D, "session_close", lambda s: 306.86)
    assert D.latest_price("SNOW", market_open=False) == 306.86
    assert D.latest_price("SNOW", market_open=True) == 368.00


def test_the_close_is_only_a_fallback(monkeypatch):
    from datetime import UTC, datetime

    from saadhak.broker import data as D

    monkeypatch.setattr(D, "last_trade", lambda s: (100.0, datetime.now(UTC)))
    monkeypatch.setattr(D, "session_close", lambda s: None)
    assert D.latest_price("X", market_open=False) == 100.0
