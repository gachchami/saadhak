"""Configuration. All secrets come from .env; nothing else reads os.environ directly."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Alpaca (paper only) ---
    apca_api_key_id: str = ""
    apca_api_secret_key: str = ""
    trading_base: str = "https://paper-api.alpaca.markets/v2"
    data_base: str = "https://data.alpaca.markets"
    options_feed: str = "indicative"  # OPRA needs a signed agreement
    stock_feed: str = "iex"

    # --- Books ---
    saadhak_books: str = "A"
    saadhak_symbols: str = "SPY,QQQ"
    saadhak_dry_run: bool = True

    # --- Book A strategy ---
    short_delta_target: float = 0.10   # only a starting point for the search sweep
    wing_width: float = 5.0
    # Gate 8 is an expectancy test derived from the exit rules, not a guessed
    # percentage-of-width floor. See engine/expectancy.py.
    min_credit_abs: float = 0.10        # take-profit must clear the penny tick
    spread_cover_multiple: float = 2.0  # credit must be 2x the spread we cross
    win_prob_margin: float = 0.03       # required edge over the breakeven win rate
    max_dte: int = 1

    # --- Risk ---
    max_loss_pct_book_a: float = 0.015
    max_loss_pct_book_b: float = 0.005
    max_portfolio_risk_pct: float = 0.06
    max_structures: int = 6
    max_per_underlying: int = 2
    daily_loss_halt_pct: float = 0.03
    total_drawdown_halt_pct: float = 0.06
    take_profit_pct: float = 0.50   # of credit received
    stop_loss_multiple: float = 2.0  # exit at 2x the credit
    proximity_pct: float = 0.003    # short strike within 0.3% of spot
    expiry_danger_pct: float = 0.004  # buffer around a short strike at the time stop
    earnings_guard: bool = True       # refuse Book A trades over an earnings event

    # --- Liquidity ---
    max_spread_pct: float = 0.15
    max_spread_abs: float = 0.10
    max_quote_age_s: float = 60.0

    # --- Calibration ---
    calibration_window: int = 40
    prior_brier: float = 0.30

    # --- Models (all OpenAI-compatible; see .env.example) ---
    saadhak_llm: str = "mock"  # mock | live
    saadhak_llm_budget_usd: float = 6.00
    practitioner_base_url: str = "https://api.featherless.ai/v1"
    practitioner_api_key: str = ""
    practitioner_model: str = "moonshotai/Kimi-K2.6"
    practitioner_reasoning_effort: str = "low"
    practitioner_max_tokens: int = 8000      # thinking is always on and eats most of this
    practitioner_timeout_s: float = 180.0
    # Featherless is the primary model provider when a key is present: an
    # OpenAI-compatible host for open-weight models, used here for the
    # practitioner's review and for the calibration study.
    featherless_api_key: str = ""
    featherless_base_url: str = "https://api.featherless.ai/v1"
    featherless_models: str = ("moonshotai/Kimi-K2.6,openai/gpt-oss-120b,"
                               "Qwen/Qwen3-235B-A22B")

    @property
    def books(self) -> list[str]:
        return [b.strip().upper() for b in self.saadhak_books.split(",") if b.strip()]

    @property
    def symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.saadhak_symbols.split(",") if s.strip()]

    @property
    def llm_key(self) -> str:
        return self.featherless_api_key or self.practitioner_api_key

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_key) and self.saadhak_llm != "mock"

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.apca_api_key_id,
            "APCA-API-SECRET-KEY": self.apca_api_secret_key,
        }


@lru_cache
def settings() -> Settings:
    return Settings()
