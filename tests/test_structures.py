from saadhak.engine.structures import closing_legs


def test_credit_and_risk_are_defined(condor):
    assert condor.width == 5.0
    assert condor.net_credit == 1.14          # (0.86-0.29) + (0.84-0.27)
    assert condor.max_loss_per_unit == 386.0  # 5*100 - 1.14*100
    assert condor.max_loss_per_unit > 0


def test_every_short_leg_is_covered(condor):
    sells = [l for l in condor.legs if l.side == "sell"]
    buys = [l for l in condor.legs if l.side == "buy"]
    assert len(buys) >= len(sells)
    assert len(condor.legs) <= 4


def test_closing_legs_mirror_the_open(condor):
    close = closing_legs(condor)
    assert [l.side for l in close] == ["buy", "sell", "buy", "sell"]
    assert all(l.position_intent.endswith("_to_close") for l in close)
    assert {l.contract.symbol for l in close} == {l.contract.symbol for l in condor.legs}
