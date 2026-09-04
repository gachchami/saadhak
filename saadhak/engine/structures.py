"""Turn a delta target into concrete option legs. The model never picks a strike; this does."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from saadhak.broker.data import Contract
from saadhak.config import settings


@dataclass(frozen=True)
class Leg:
    contract: Contract
    side: str            # buy | sell
    position_intent: str  # buy_to_open | sell_to_open | buy_to_close | sell_to_close
    ratio_qty: int = 1

    def to_api(self) -> dict:
        return {"symbol": self.contract.symbol, "ratio_qty": str(self.ratio_qty),
                "side": self.side, "position_intent": self.position_intent}


@dataclass
class Structure:
    kind: str                 # iron_condor | put_credit_spread | call_credit_spread
    underlying: str
    expiry: date
    legs: list[Leg]
    qty: int = 1
    book: str = "A"
    meta: dict = field(default_factory=dict)

    @property
    def is_credit(self) -> bool:
        return self.kind in ("iron_condor", "put_credit_spread", "call_credit_spread")

    @property
    def net_credit(self) -> float:
        """Per-spread credit at the mid, in dollars per contract-unit."""
        total = 0.0
        for leg in self.legs:
            m = leg.contract.mid * leg.ratio_qty
            total += m if leg.side == "sell" else -m
        return round(total, 2)

    @property
    def width(self) -> float:
        """Widest strike gap within a single vertical of the structure."""
        puts = sorted([l.contract.strike for l in self.legs if l.contract.kind == "put"])
        calls = sorted([l.contract.strike for l in self.legs if l.contract.kind == "call"])
        widths = []
        if len(puts) >= 2:
            widths.append(max(puts) - min(puts))
        if len(calls) >= 2:
            widths.append(max(calls) - min(calls))
        return max(widths) if widths else 0.0

    @property
    def max_loss_per_unit(self) -> float:
        """Defined risk: width x 100 minus the credit taken in."""
        return round(self.width * 100 - self.net_credit * 100, 2)

    @property
    def max_loss(self) -> float:
        return round(self.max_loss_per_unit * self.qty, 2)

    @property
    def short_legs(self) -> list[Leg]:
        return [l for l in self.legs if l.side == "sell"]

    @property
    def short_strikes(self) -> list[float]:
        return [l.contract.strike for l in self.short_legs]

    def describe(self) -> str:
        ks = "/".join(f"{l.contract.strike:g}" for l in sorted(self.legs, key=lambda l: l.contract.strike))
        return f"{self.underlying} {self.expiry} {self.kind} {ks} x{self.qty} @ {self.net_credit:+.2f}"


def _pick_by_delta(cands: list[Contract], target: float) -> Contract | None:
    usable = [c for c in cands if c.delta is not None and c.bid > 0]
    if not usable:
        return None
    return min(usable, key=lambda c: abs(c.abs_delta - target))


def _wing(cands: list[Contract], short: Contract, width: float, kind: str) -> Contract | None:
    """The long leg: `width` further out of the money than the short leg."""
    want = short.strike - width if kind == "put" else short.strike + width
    same = [c for c in cands if c.kind == kind]
    if not same:
        return None
    exact = [c for c in same if abs(c.strike - want) < 1e-6]
    if exact:
        return exact[0]
    # nearest strike strictly further OTM than the short
    further = [c for c in same if (c.strike < short.strike if kind == "put" else c.strike > short.strike)]
    return min(further, key=lambda c: abs(c.strike - want)) if further else None


def build_credit_spread(chain_: list[Contract], kind: str, *, delta_target: float | None = None,
                        width: float | None = None, book: str = "A") -> Structure | None:
    s = settings()
    delta_target = delta_target or s.short_delta_target
    width = width or s.wing_width
    side = [c for c in chain_ if c.kind == kind]
    short = _pick_by_delta(side, delta_target)
    if not short:
        return None
    long_ = _wing(side, short, width, kind)
    if not long_ or long_.symbol == short.symbol:
        return None
    legs = [
        Leg(short, "sell", "sell_to_open"),
        Leg(long_, "buy", "buy_to_open"),
    ]
    return Structure(
        kind="put_credit_spread" if kind == "put" else "call_credit_spread",
        underlying=short.underlying, expiry=short.expiry, legs=legs, book=book,
        meta={"short_delta": short.delta, "greeks_source": short.greeks_source},
    )


def build_iron_condor(chain_: list[Contract], *, delta_target: float | None = None,
                      width: float | None = None, book: str = "A",
                      drift_aware: bool = True) -> Structure | None:
    """A condor whose two sides are placed by breach frequency, not by equal delta.

    Selling both sides at the same delta assumes a symmetric distribution. It is
    not symmetric: at the distances we trade, the index breaches the call side
    about 1.4 times as often as the put side.
    """
    s = settings()
    base = delta_target or s.short_delta_target
    put_target = call_target = base
    if drift_aware and chain_:
        from saadhak.engine.drift import measure
        a = measure(chain_[0].underlying)
        if a:
            put_target, call_target = a.put_delta(base), a.call_delta(base)

    put_side = build_credit_spread(chain_, "put", delta_target=put_target, width=width, book=book)
    call_side = build_credit_spread(chain_, "call", delta_target=call_target, width=width, book=book)
    if not put_side or not call_side:
        return None
    return Structure(
        kind="iron_condor", underlying=put_side.underlying, expiry=put_side.expiry,
        legs=put_side.legs + call_side.legs, book=book,
        meta={"put_delta": put_side.meta.get("short_delta"),
              "call_delta": call_side.meta.get("short_delta"),
              "put_target": put_target, "call_target": call_target,
              "greeks_source": put_side.meta.get("greeks_source")},
    )


def closing_legs(structure: Structure) -> list[Leg]:
    """Mirror an open structure to flatten it."""
    flip = {"sell_to_open": ("buy", "buy_to_close"), "buy_to_open": ("sell", "sell_to_close")}
    out = []
    for leg in structure.legs:
        side, intent = flip[leg.position_intent]
        out.append(Leg(leg.contract, side, intent, leg.ratio_qty))
    return out
