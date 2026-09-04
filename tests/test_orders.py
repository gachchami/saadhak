"""Alpaca prices multi-leg orders as a signed net. Getting the sign wrong turns
'require at least this credit' into 'willing to pay up to this debit'."""
from saadhak.broker.orders import build_body, signed_limit


def test_credit_structures_send_a_negative_limit(condor):
    assert condor.is_credit
    assert signed_limit(condor, 0.22) == -0.22
    body = build_body(condor, condor.net_credit)
    assert body["limit_price"].startswith("-"), body["limit_price"]
    assert float(body["limit_price"]) == -1.14


def test_body_shape_is_what_alpaca_accepts(condor):
    body = build_body(condor, condor.net_credit, cycle_id="c1")
    assert body["order_class"] == "mleg"
    assert body["type"] == "limit"
    assert body["time_in_force"] == "day"
    assert len(body["legs"]) == 4
    assert len(body["client_order_id"]) == 32
    for leg in body["legs"]:
        assert set(leg) == {"symbol", "ratio_qty", "side", "position_intent"}
