"""Account, clock, calendar, positions, portfolio history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from saadhak.broker.client import trading


@dataclass(frozen=True)
class Account:
    id: str
    account_number: str
    equity: float
    cash: float
    options_buying_power: float
    options_level: int
    last_equity: float

    @property
    def daily_pl(self) -> float:
        return self.equity - self.last_equity

    @property
    def daily_pl_pct(self) -> float:
        return self.daily_pl / self.last_equity if self.last_equity else 0.0


def get_account() -> Account:
    d = trading("/account")
    return Account(
        id=d["id"],
        account_number=d["account_number"],
        equity=float(d["equity"]),
        cash=float(d["cash"]),
        options_buying_power=float(d.get("options_buying_power") or 0),
        options_level=int(d.get("options_trading_level") or 0),
        last_equity=float(d.get("last_equity") or d["equity"]),
    )


def get_clock() -> dict:
    return trading("/clock")


def is_open() -> bool:
    return bool(get_clock()["is_open"])


def minutes_since_open() -> float | None:
    """Minutes since the session opened, or None when the market is closed."""
    c = get_clock()
    if not c["is_open"]:
        return None
    now = datetime.fromisoformat(c["timestamp"]).astimezone(UTC)
    # next_close is today's close; the open was 6.5h before it
    close = datetime.fromisoformat(c["next_close"]).astimezone(UTC)
    return (now - (close - timedelta(hours=6, minutes=30))).total_seconds() / 60.0


def minutes_to_close() -> float | None:
    c = get_clock()
    if not c["is_open"]:
        return None
    now = datetime.fromisoformat(c["timestamp"]).astimezone(UTC)
    close = datetime.fromisoformat(c["next_close"]).astimezone(UTC)
    return (close - now).total_seconds() / 60.0


def get_positions() -> list[dict]:
    return trading("/positions") or []


def option_positions() -> list[dict]:
    return [p for p in get_positions() if p.get("asset_class") == "us_option"]


def portfolio_history(period: str = "1W", timeframe: str = "1D") -> dict:
    return trading("/account/portfolio/history",
                   params={"period": period, "timeframe": timeframe})


def calendar(start: str, end: str) -> list[dict]:
    return trading("/calendar", params={"start": start, "end": end})
