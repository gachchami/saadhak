"""Choose the structure. The engine searches the achievable surface and picks the
best expectancy that clears every gate; nothing here is a hand-picked constant.

This is the piece that replaces a human deciding "use $5 wings at 10 delta". Those
were guesses that happened to be incompatible with the market. The search below
measures what the chain actually pays today and takes the best positive-expectancy
structure, or refuses when there is none.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from saadhak.broker.data import Contract
from saadhak.engine.expectancy import Expectancy, evaluate as expectancy_of
from saadhak.engine.structures import Structure, build_iron_condor

# The search space. Deltas span the sensible short-strike range; widths span the
# strike increments SPY and QQQ actually list.
DELTAS = (0.06, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25)
WIDTHS = (1.0, 2.0, 3.0, 5.0, 10.0)


@dataclass
class Candidate:
    structure: Structure
    expectancy: Expectancy
    expiry: date
    delta_target: float
    width: float

    @property
    def score(self) -> float:
        """Expected value per dollar of capital at risk."""
        risk = self.structure.max_loss_per_unit
        return (self.expectancy.ev_per_contract * 100) / risk if risk > 0 else -1e9

    def row(self) -> dict:
        return {
            "expiry": self.expiry.isoformat(), "delta_target": self.delta_target,
            "width": self.width, "credit": self.structure.net_credit,
            "max_loss_per_unit": self.structure.max_loss_per_unit,
            "win_prob": round(self.expectancy.win_prob, 4),
            "breakeven": round(self.expectancy.breakeven_prob, 4),
            "ev_per_contract": round(self.expectancy.ev_per_contract, 4),
            "score": round(self.score, 5),
            "ok": self.expectancy.ok, "reason": self.expectancy.reason,
        }


@dataclass
class Search:
    candidates: list[Candidate] = field(default_factory=list)
    considered: int = 0

    @property
    def viable(self) -> list[Candidate]:
        return sorted([c for c in self.candidates if c.expectancy.ok],
                      key=lambda c: c.score, reverse=True)

    @property
    def best(self) -> Candidate | None:
        v = self.viable
        return v[0] if v else None

    def journal_rows(self, limit: int = 12) -> list[dict]:
        ranked = sorted(self.candidates, key=lambda c: c.score, reverse=True)
        return [c.row() for c in ranked[:limit]]


def search(chains: dict[date, list[Contract]], *, book: str = "A") -> Search:
    """Build every (expiry, delta, width) condor available and score it."""
    s = Search()
    seen: set[tuple] = set()
    for expiry, contracts in chains.items():
        if not contracts:
            continue
        for d in DELTAS:
            for w in WIDTHS:
                st = build_iron_condor(contracts, delta_target=d, width=w, book=book)
                s.considered += 1
                if not st or st.width <= 0:
                    continue
                key = tuple(sorted(l.contract.symbol for l in st.legs))
                if key in seen:
                    continue          # different targets landed on the same strikes
                seen.add(key)
                s.candidates.append(Candidate(st, expectancy_of(st), expiry, d, st.width))
    return s
