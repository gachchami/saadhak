# Saadhak — interfaces

*Draft v0 (design-time). Replace examples with real emitted output as the build lands.*

## 1. Command line (`uv run saadhak …`)
| Command | Purpose | Output | Exit codes |
|---|---|---|---|
| `status` | Account, clock, next entry window, SPY/QQQ chain slice with deltas | JSON (or table with `--pretty`) | 0 ok · 2 auth failure |
| `run [--dry-run] [--book A,B] [--symbols SPY,QQQ]` | Start the loop (entries at fixed windows, practitioner every 30 min, monitor every 60 s) | Log lines + journal writes | 0 on `STOP`/SIGTERM · 1 on fatal |
| `kill` | Cancel all orders, close all positions (wraps `ops/kill.sh`) | Summary JSON | 0 |
| `report [--date YYYY-MM-DD]` | P&L, trades, refusals, calibration for a day; markdown for social posts | Markdown | 0 |
| `practice --days N` *(stretch)* | Replay the last N sessions to seed calibration | Calibration JSON | 0 |

## 2. Ops scripts (Alpaca CLI, `ops/`)
| Script | Commands used | Notes |
|---|---|---|
| `kill.sh` | `alpaca order cancel-all`, `alpaca position close-all` | Idempotent; safe to run twice |
| `eod_report.sh` | `alpaca position list --jq …`, `alpaca account portfolio-history …` | Prints markdown |
| `healthcheck.sh` | `alpaca clock`, `alpaca account get --jq .status` | Exit 0 healthy, 1 unhealthy, 2 auth |
| `validate_orders.sh` | `alpaca order submit --dry-run --order-class mleg --legs …` | Used in CI to validate journaled order bodies |

Auth for the CLI comes from `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` (mapped from the `APCA_*` values in `.env`). Paper is the default; live is never enabled.

## 3. State file — `state/latest.json` (dashboard contract)
```json
{
  "as_of": "2026-09-02T14:35:10Z",
  "account": {"id": "…", "equity": 100812.4, "cash": 98210.1, "daily_pl": 812.4, "drawdown_pct": 0.0},
  "halted": false, "halt_reason": null,
  "calibration": {"brier": 0.19, "n_resolved": 23, "multiplier": 0.82},
  "open_structures": [{"id": "…", "underlying": "SPY", "kind": "iron_condor", "expiry": "2026-09-02",
                       "legs": ["SPY260902P00752000", "…"], "qty": 3, "credit": 1.02, "max_loss": 1194.0,
                       "unrealized_pl": 96.0, "next_exit_rule": "tp_50pct"}],
  "last_reconciliation": {"at": "2026-09-02T14:30:00Z", "ok": true, "diff": []},
  "journal_head": "sha256:…"
}
```

## 4. Journal — `journal/YYYY-MM-DD.jsonl` (append-only, hash-chained)
Every line: `{"seq", "ts", "type", "prev_hash", "hash", "data"}` where `hash = sha256(prev_hash + canonical_json(data))`.

| `type` | `data` fields |
|---|---|
| `cycle_start` | `cycle_id`, `book`, `symbols`, `clock` |
| `thesis` | the practitioner schema (see PLAN.md §4) plus `model`, `mcp_tools_called[]`, `latency_ms` |
| `adversary` | `model`, `rebuttal`, `latency_ms` |
| `gate_result` | `structure_id`, `gates: [{n, name, ok, reason}]`, `decision: accept|refuse` |
| `order_submitted` | `client_order_id`, `alpaca_order_id`, `body` (the mleg request), `attempt`, `limit_price` |
| `order_filled` / `order_unfilled` | `alpaca_order_id`, `filled_avg_price`, `qty` |
| `exit` | `structure_id`, `rule` (`tp_50pct|sl_2x|time_stop|proximity|halt|kill`), `pl` |
| `forecast` / `forecast_resolved` | `symbol`, `lo`, `hi`, `p`, `outcome`, `brier_contribution` |
| `reconciliation` | `ok`, `diff[]`, `source: "alpaca-cli"` |
| `halt` | `reason` |

## 5. Optional HTTP (stretch S2, FastAPI)
`GET /health` → `{ok, as_of}` · `GET /state` → the state file · `GET /journal?date=` → JSONL lines · `POST /kill` (local only, requires `X-Kill-Token`).

## 6. Alpaca surfaces used
**Trading API (alpaca-py, paper):** `GET /v2/account`, `GET /v2/clock`, `GET /v2/calendar`, `GET /v2/account/portfolio/history`, `GET /v2/options/contracts`, `POST /v2/orders` (`order_class: "mleg"`, `type: "limit"`, `time_in_force: "day"`, `legs[]` with `symbol`, `ratio_qty`, `side`, `position_intent`), `PATCH /v2/orders/{id}` (limit walk), `DELETE /v2/orders/{id}`, `GET /v2/positions`, `DELETE /v2/positions/{symbol}`.

**Market Data API:** `GET /v1beta1/options/snapshots/{underlying}` (`feed=indicative`, greeks + IV when available), `GET /v1beta1/options/snapshots?symbols=`, `GET /v2/stocks/{symbol}/bars`, `GET /v2/stocks/{symbol}/quotes/latest` (`feed=iex`), `GET /v1beta1/news`.

**MCP server (`uvx alpaca-mcp-server`, stdio, `ALPACA_TOOLSETS=options-data,stock-data,news,account`):** `get_option_chain`, `get_option_snapshot`, `get_option_contracts`, `get_stock_snapshot`, `get_stock_bars`, `get_news`, `get_account_info`, `get_all_positions`, `get_clock`, `search_alpaca_docs`. The `trading` toolset is deliberately not loaded.

**CLI:** see §2.

## 7. Model providers
- Featherless (OpenAI-compatible, `https://Featherless/v1`, `a Featherless model`, API currently billed at 0 credits): routine practitioner cycles and micro-forecasts; the client paces itself (limits are undocumented) and falls back to Featherless on 429 or quota errors.
- Featherless (OpenAI-compatible, `https://api.featherless.ai/v1`): catalyst decisions `moonshotai/Kimi-K2.6`, adversary `openai/gpt-oss-120b`, fallback `a Featherless model`; JSON-schema output validated with Pydantic, one retry; 90-s budget per call. Covered by the $25 hackathon credit.
- Anthropic (optional, `PRACTITIONER_PROVIDER=anthropic`): `claude-opus-5` for a premium run; `claude-haiku-4-5` as the cheap overflow fallback.
