"""Whether a structure is worth taking, derived from our own exit rules.

A fixed "credit must be N% of width" floor is a guess. It also measures the wrong
thing: we never hold to max loss, because the monitor exits at a multiple of the
credit. So the payoff is set by the exit rules, not by the width.

With take-profit at `tp` of the credit and a stop at `sl` times the credit:

    win  = +tp * C          (default +0.50 C)
    loss = -(sl - 1) * C    (default -1.00 C)

Breakeven win rate is loss / (win + loss) = 2/3 with the defaults. So the real
question is whether this structure wins more than two times in three. Delta is
the market's own estimate of finishing in the money, so for a condor:

    P(win) ~ (1 - |delta_put|) * (1 - |delta_call|)

That is deliberately conservative: it counts any in-the-money finish as a loss,
while in practice the stop often exits for less than a full loss and some
touched structures recover. Two mechanical floors sit alongside it, because an
edge that is thinner than the tick size or the spread is not an edge.

The expected value is net of friction. Crossing the bid-ask costs the same in
cents whether a structure is one point wide or ten, so it is a fixed toll on a
credit that grows with width -- on a narrow spread it can be half the edge. A
gross expected value is scale-free and therefore ranks the narrowest structure
first every time, which is how a search over widths ends up choosing spreads too
small to fill or to manage. Charging the round trip inside the number removes
that bias without anyone having to express a preference about width.
"""
from __future__ import annotations

from dataclasses import dataclass

from saadhak.config import settings
from saadhak.engine.structures import Structure


@dataclass(frozen=True)
class Expectancy:
    win_prob: float
    breakeven_prob: float
    credit: float
    win_amount: float
    loss_amount: float
    ev_per_contract: float
    spread_cost: float
    ok: bool
    reason: str

    def explain(self) -> str:
        return (f"P(win) {self.win_prob:.0%} vs breakeven {self.breakeven_prob:.0%}, "
                f"EV ${self.ev_per_contract:+.2f}/contract on ${self.credit:.2f} credit")


def win_probability(structure: Structure) -> float | None:
    """Probability that every short leg expires out of the money, from delta."""
    deltas = [abs(l.contract.delta) for l in structure.short_legs
              if l.contract.delta is not None]
    if not deltas:
        return None
    p = 1.0
    for d in deltas:
        p *= (1.0 - min(d, 1.0))
    return p


def natural_credit(structure: Structure) -> float:
    """The credit available immediately: sell every short leg at the bid, pay the
    ask on every long one. This is the price at which the order is marketable."""
    total = 0.0
    for leg in structure.legs:
        px = leg.contract.bid if leg.side == "sell" else -leg.contract.ask
        total += px * leg.ratio_qty
    return round(total, 2)


def spread_cost(structure: Structure) -> float:
    """Half the bid-ask on every leg: what crossing the spread costs to get in."""
    return sum(l.contract.spread / 2.0 * l.ratio_qty for l in structure.legs)


def evaluate(structure: Structure) -> Expectancy:
    s = settings()
    credit = structure.net_credit
    win_amt = credit * s.take_profit_pct
    loss_amt = credit * (s.stop_loss_multiple - 1.0)
    breakeven = loss_amt / (win_amt + loss_amt) if (win_amt + loss_amt) > 0 else 1.0

    p = win_probability(structure)
    sc = spread_cost(structure)
    friction = sc * 2.0   # cross the spread to get in, and again to get out
    ev = (p * win_amt - (1 - p) * loss_amt - friction) if p is not None else 0.0

    if p is None:
        return Expectancy(0, breakeven, credit, win_amt, loss_amt, 0, sc, False,
                          "no deltas available to estimate win probability")
    if credit < s.min_credit_abs:
        return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, False,
                          f"credit ${credit:.2f} below ${s.min_credit_abs:.2f} minimum "
                          f"(take-profit would be under a tick)")
    if credit < sc * s.spread_cover_multiple:
        return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, False,
                          f"credit ${credit:.2f} under {s.spread_cover_multiple:g}x the "
                          f"${sc:.2f} spread cost")
    if p < breakeven + s.win_prob_margin:
        return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, False,
                          f"P(win) {p:.0%} below breakeven {breakeven:.0%} "
                          f"+ {s.win_prob_margin:.0%} margin")

    # Alpaca paper fills only what is marketable. If the price that would fill is
    # already below the least credit worth taking, there is no price at which this
    # trade both fills and is worth filling -- and posting it produces a dead
    # order that occupies the book's caps until it is swept.
    nat = natural_credit(structure)
    floor = max(s.min_credit_abs, sc * s.spread_cover_multiple)
    if nat < floor:
        return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, False,
                          f"unfillable: marketable credit ${nat:.2f} is below the "
                          f"${floor:.2f} reservation, so no fill clears the floor")

    if ev <= 0:
        return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, False,
                          f"EV ${ev:+.2f}/contract after ${friction:.2f} round-trip "
                          f"friction: the spread eats the edge")

    return Expectancy(p, breakeven, credit, win_amt, loss_amt, ev, sc, True,
                      f"P(win) {p:.0%} beats breakeven {breakeven:.0%} by "
                      f"{p - breakeven:.0%}; EV ${ev:+.2f}/contract net of "
                      f"${friction:.2f} friction")


def reservation_credit(structure: Structure) -> float:
    """The least credit at which this structure still clears the expectancy test.

    Of the three acceptance conditions, only two move with the price. The
    win-probability margin does not: take-profit and stop both scale with the
    credit, so the breakeven win rate is the same at any price. That leaves the
    tick floor and the spread-cover rule, and the binding one of the two is the
    reservation price.

    An entry limit may be walked toward the natural price to get filled, but
    never past this number. Below it the fill is bought by giving away the
    reason the trade was taken.
    """
    s = settings()
    return round(max(s.min_credit_abs, spread_cost(structure) * s.spread_cover_multiple), 2)
