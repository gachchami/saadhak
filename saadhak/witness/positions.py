"""Reconstruct open structures from the broker's own position list.

Deliberately independent of the journal: if the process restarts, or the journal
is lost, the monitor still knows what is open and what it was worth at entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from saadhak.broker import account as acct
from saadhak.broker.data import _parse_occ


@dataclass
class OpenLeg:
    symbol: str
    qty: int                 # negative when short
    avg_entry_price: float
    current_price: float
    market_value: float
    strike: float
    kind: str
    expiry: date

    @property
    def is_short(self) -> bool:
        return self.qty < 0


@dataclass
class OpenStructure:
    underlying: str
    expiry: date
    legs: list[OpenLeg]

    @property
    def contracts(self) -> int:
        return max(abs(l.qty) for l in self.legs)

    @property
    def entry_credit(self) -> float:
        """Per contract. Positive means we were paid to open."""
        return round(sum(l.avg_entry_price * (1 if l.is_short else -1) for l in self.legs), 4)

    @property
    def cost_to_close(self) -> float:
        """Per contract. Positive means we must pay to get out."""
        return round(-sum(l.market_value for l in self.legs) / (self.contracts * 100), 4)

    @property
    def unrealised(self) -> float:
        return round((self.entry_credit - self.cost_to_close) * self.contracts * 100, 2)

    @property
    def short_strikes(self) -> list[float]:
        return [l.strike for l in self.legs if l.is_short]

    def threatened_shorts(self, spot: float, buffer: float) -> list[str]:
        """Short legs at risk of finishing in the money, within a price buffer.

        A short put is threatened from below, a short call from above. Anything
        outside the buffer will expire worthless and should be left alone."""
        out = []
        for l in self.legs:
            if not l.is_short:
                continue
            if l.kind == "put" and spot <= l.strike + buffer:
                out.append(f"{l.strike:g}P (spot {spot:.2f} within {buffer:.2f})")
            elif l.kind == "call" and spot >= l.strike - buffer:
                out.append(f"{l.strike:g}C (spot {spot:.2f} within {buffer:.2f})")
        return out

    @property
    def width(self) -> float:
        puts = sorted(l.strike for l in self.legs if l.kind == "put")
        calls = sorted(l.strike for l in self.legs if l.kind == "call")
        w = []
        if len(puts) >= 2:
            w.append(max(puts) - min(puts))
        if len(calls) >= 2:
            w.append(max(calls) - min(calls))
        return max(w) if w else 0.0

    @property
    def max_loss(self) -> float:
        return round((self.width - self.entry_credit) * 100 * self.contracts, 2)

    def describe(self) -> str:
        ks = "/".join(f"{l.strike:g}" for l in sorted(self.legs, key=lambda l: l.strike))
        return f"{self.underlying} {self.expiry} {ks} x{self.contracts} @ {self.entry_credit:+.2f}"

    def closing_legs(self) -> list[dict]:
        out = []
        for l in self.legs:
            side = "buy" if l.is_short else "sell"
            intent = "buy_to_close" if l.is_short else "sell_to_close"
            out.append({"symbol": l.symbol,
                        "ratio_qty": str(abs(l.qty) // self.contracts),
                        "side": side, "position_intent": intent})
        return out


def open_structures() -> list[OpenStructure]:
    groups: dict[tuple, list[OpenLeg]] = {}
    for p in acct.option_positions():
        root, expiry, kind, strike = _parse_occ(p["symbol"])
        leg = OpenLeg(
            symbol=p["symbol"], qty=int(p["qty"]),
            avg_entry_price=float(p["avg_entry_price"]),
            current_price=float(p.get("current_price") or 0),
            market_value=float(p.get("market_value") or 0),
            strike=strike, kind=kind, expiry=expiry,
        )
        groups.setdefault((root, expiry), []).append(leg)
    return [OpenStructure(u, e, legs) for (u, e), legs in groups.items()]
