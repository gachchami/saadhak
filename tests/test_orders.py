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


"""The walk. Alpaca paper fills only what is marketable now, so an entry left at
the mid never fills; and a walk with no floor buys the fill by giving the trade
away. Both halves are tested here."""
import saadhak.broker.orders as orders_mod
from saadhak.broker.orders import OrderResult, walk_limit
from saadhak.engine.expectancy import reservation_credit


class _Broker:
    """Records every PATCH. Never fills, so the walk runs to its bound."""

    def __init__(self, fill_on_step=None):
        self.patched, self.cancelled, self.calls = [], [], 0
        self.fill_on_step = fill_on_step

    def get_order(self, order_id):
        self.calls += 1
        if self.fill_on_step and self.calls >= self.fill_on_step:
            return {"id": order_id, "status": "filled"}
        return {"id": order_id, "status": "new"}

    def trading(self, path, method="GET", json=None, params=None):
        if method == "PATCH":
            self.patched.append(float(json["limit_price"]))
            return {"id": path.rsplit("/", 1)[-1], "status": "new"}
        return {}

    def cancel(self, order_id):
        self.cancelled.append(order_id)


def _install(monkeypatch, broker):
    monkeypatch.setattr(orders_mod, "get_order", broker.get_order)
    monkeypatch.setattr(orders_mod, "trading", broker.trading)
    monkeypatch.setattr(orders_mod, "cancel", broker.cancel)
    monkeypatch.setattr(orders_mod.time, "sleep", lambda _s: None)


def _submitted(condor):
    return OrderResult(True, False, {}, {"id": "o1", "status": "new"})


def test_walk_steps_the_limit_toward_the_natural_price(monkeypatch, condor):
    b = _Broker()
    _install(monkeypatch, b)
    walk_limit(condor, _submitted(condor))
    assert b.patched, "the walk never repriced the order"
    # Signed: a credit is negative, so giving up credit means rising toward zero.
    assert b.patched == sorted(b.patched), b.patched
    assert b.patched[0] > float(f"{-condor.net_credit:.2f}")


def test_walk_never_prices_below_the_reservation_credit(monkeypatch, condor):
    b = _Broker()
    _install(monkeypatch, b)
    walk_limit(condor, _submitted(condor))
    floor = -reservation_credit(condor)
    for price in b.patched:
        assert price <= floor + 1e-9, f"walked to {price}, past the {floor} floor"


def test_walk_stops_and_cancels_when_it_cannot_fill(monkeypatch, condor):
    b = _Broker()
    _install(monkeypatch, b)
    res = walk_limit(condor, _submitted(condor))
    assert b.cancelled == ["o1"], "an unfillable order must not be left resting"
    assert res.submitted


def test_walk_stops_the_moment_it_fills(monkeypatch, condor):
    b = _Broker(fill_on_step=1)
    _install(monkeypatch, b)
    res = walk_limit(condor, _submitted(condor))
    assert res.status == "filled"
    assert b.patched == [], "a filled order must not be repriced"
    assert b.cancelled == []


def test_a_structure_with_no_slack_is_not_walked(monkeypatch, condor):
    """When the mid already sits at the reservation price there is nothing to spend."""
    b = _Broker()
    _install(monkeypatch, b)
    monkeypatch.setattr(orders_mod, "reservation_credit", lambda st: st.net_credit)
    walk_limit(condor, _submitted(condor))
    assert b.patched == []
    assert b.cancelled == ["o1"]
