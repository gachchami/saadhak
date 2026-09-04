from __future__ import annotations
from datetime import UTC, date, datetime, timedelta

import pytest

from saadhak.broker.data import Contract
from saadhak.engine.structures import Leg, Structure


def mk_contract(symbol="SPY260904P00750000", kind="put", strike=750.0, *, bid=1.00,
                ask=1.04, delta=-0.10, volume=5000, expiry=None, age_s=1.0):
    return Contract(
        symbol=symbol, underlying="SPY", kind=kind, strike=strike,
        expiry=expiry or (datetime.now(UTC).date() + timedelta(days=1)),
        bid=bid, ask=ask, quote_ts=datetime.now(UTC) - timedelta(seconds=age_s),
        delta=delta, iv=0.17, volume=volume, greeks_source="computed",
    )


@pytest.fixture
def condor():
    """A well-formed iron condor: $5 wings, $1.14 credit (22.8% of width, clears the floor)."""
    sp = mk_contract("SPY..P00750000", "put", 750.0, bid=0.85, ask=0.87, delta=-0.10)
    lp = mk_contract("SPY..P00745000", "put", 745.0, bid=0.28, ask=0.30, delta=-0.05)
    sc = mk_contract("SPY..C00775000", "call", 775.0, bid=0.83, ask=0.85, delta=0.10)
    lc = mk_contract("SPY..C00780000", "call", 780.0, bid=0.26, ask=0.28, delta=0.05)
    return Structure(
        kind="iron_condor", underlying="SPY", expiry=sp.expiry,
        legs=[Leg(sp, "sell", "sell_to_open"), Leg(lp, "buy", "buy_to_open"),
              Leg(sc, "sell", "sell_to_open"), Leg(lc, "buy", "buy_to_open")],
        qty=1, book="A",
    )
