"""Multi-leg order construction and submission. The ONLY path that creates an order."""
from __future__ import annotations

import time
from dataclasses import dataclass

from saadhak.broker.client import AlpacaError, trading
from saadhak.config import settings
from saadhak.engine.expectancy import reservation_credit
from saadhak.engine.gates import client_order_id
from saadhak.engine.structures import Leg, Structure


@dataclass
class OrderResult:
    submitted: bool
    dry_run: bool
    body: dict
    response: dict | None = None
    error: str | None = None

    @property
    def order_id(self) -> str | None:
        return (self.response or {}).get("id")

    @property
    def status(self) -> str:
        if self.error:
            return "error"
        if self.dry_run:
            return "dry_run"
        return (self.response or {}).get("status", "unknown")


def signed_limit(structure: Structure, price: float) -> float:
    """Alpaca prices multi-leg orders as a SIGNED net: negative is a credit we
    receive, positive is a debit we pay. Sending a positive number for a credit
    spread reads as "willing to pay up to this much", which is the opposite of
    the intent and silently widens the worst case by the debit paid."""
    return -abs(price) if structure.is_credit else abs(price)


def build_body(structure: Structure, limit_price: float, *, legs: list[Leg] | None = None,
               cycle_id: str = "") -> dict:
    """An mleg limit order. Alpaca requires limit orders for multi-leg; we never send market."""
    legs = legs or structure.legs
    return {
        "order_class": "mleg",
        "qty": str(structure.qty),
        "type": "limit",
        "time_in_force": "day",
        "limit_price": f"{signed_limit(structure, limit_price):.2f}",
        "client_order_id": client_order_id(structure, cycle_id),
        "legs": [l.to_api() for l in legs],
    }


def submit(structure: Structure, *, dry_run: bool, limit_price: float | None = None,
           legs: list[Leg] | None = None, cycle_id: str = "") -> OrderResult:
    price = limit_price if limit_price is not None else structure.net_credit
    body = build_body(structure, price, legs=legs, cycle_id=cycle_id)
    if dry_run:
        return OrderResult(submitted=False, dry_run=True, body=body)
    try:
        resp = trading("/orders", method="POST", json=body)
        return OrderResult(submitted=True, dry_run=False, body=body, response=resp)
    except AlpacaError as e:
        return OrderResult(submitted=False, dry_run=False, body=body, error=str(e))


def get_order(order_id: str) -> dict:
    return trading(f"/orders/{order_id}")


def cancel(order_id: str) -> None:
    trading(f"/orders/{order_id}", method="DELETE")


def open_orders() -> list[dict]:
    return trading("/orders", params={"status": "open", "limit": 100}) or []


def walk_limit(structure: Structure, result: OrderResult, *, steps: int | None = None,
               wait_s: float | None = None, cycle_id: str = "",
               on_step=None) -> OrderResult:
    """Step an unfilled entry toward the natural price, then cancel what will not fill.

    Alpaca's paper environment only fills an order that is marketable against the
    NBBO right now; it never simulates a resting order being taken. An entry
    posted at the mid and left alone therefore cannot fill, however long it waits.

    Credit structures walk *down* (accept less credit); debits walk *up*. In
    Alpaca's signed convention both directions are the same arithmetic: worse for
    us is always more positive, so one clamp bounds both. That bound is the
    structure's reservation price -- the walk buys a fill with the slack the
    expectancy test allows and stops at the point where the trade stops being
    worth taking.
    """
    if not result.submitted or not result.order_id:
        return result
    s = settings()
    steps = s.walk_steps if steps is None else steps
    wait_s = s.walk_wait_s if wait_s is None else wait_s
    if steps < 1:
        return result
    # Both in signed terms: negative is credit received.
    natural = -sum(
        (l.contract.bid if l.side == "sell" else -l.contract.ask) * l.ratio_qty
        for l in structure.legs
    )
    start = signed_limit(structure, structure.net_credit)
    # Never walk past the price at which the trade stops clearing its own
    # expectancy test. Signed, "worse for us" is more positive either way.
    bound = signed_limit(structure, reservation_credit(structure))
    order_id = result.order_id
    sent = start
    for i in range(1, steps + 1):
        time.sleep(wait_s)
        o = get_order(order_id)
        if o.get("status") in ("filled", "canceled", "expired", "rejected"):
            return OrderResult(True, False, result.body, o)
        target = round(min(start + (natural - start) * (i / steps), bound), 2)
        if target <= sent:      # no slack left, or already there
            break
        try:
            o = trading(f"/orders/{order_id}", method="PATCH",
                        json={"limit_price": f"{target:.2f}"})
            order_id = o.get("id", order_id)
            sent = target
            if on_step:
                on_step(order_id, target, i)
        except AlpacaError:
            break
    try:
        o = get_order(order_id)
        if o.get("status") not in ("filled", "canceled", "expired", "rejected"):
            cancel(order_id)
            o = get_order(order_id)
        return OrderResult(True, False, result.body, o)
    except AlpacaError as e:
        return OrderResult(True, False, result.body, result.response, error=str(e))
