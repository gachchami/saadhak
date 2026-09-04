# Saadhak — instructions for agents working in this repo

Saadhak is an autonomous, defined-risk options trading agent on Alpaca's **paper** environment, built for the lablaFeatherless × Alpaca AI Trading Agents Hackathon (deadline Fri 4 Sep 2026, 20:30 IST). The full plan is in `PLAN.md`; read it before changing strategy, gates, or schedule.

## Directories agents must ignore
- `human-docs/` is human-facing documentation (app overview, API reference, user stories). **Do not read, search, index, summarize, or edit it** unless the user names that directory explicitly in their request. It is not a source of truth for code. The same rule is mirrored for other tools in `.aiexclude`, `.cursorignore`, and `.codeiumignore`.
- To make this a hard rule for Claude Code, add to `.claude/settings.json`: `{"permissions": {"deny": ["Read(./human-docs/**)", "Edit(./human-docs/**)", "Write(./human-docs/**)"]}}`. It is intentionally left soft so a human can still ask for an update.

## Non-negotiables
- Paper trading only. Never set `ALPACA_LIVE_TRADE`, never use live endpoints.
- `.env` is never committed. Secrets are read only through `saadhak/config.py`.
- Options orders are always `order_class: "mleg"` limit orders with every leg inside the order. Never market orders for options. Never naked short legs.
- Only `saadhak/engine/` may build or submit orders. The practitioner (LLM) never sees `POST /v2/orders`, and the MCP server it uses is started **without** the `trading` toolset.
- Every order carries a deterministic `client_order_id`.
- All internal timestamps are UTC. Eastern time appears only in the scheduler; IST only in docs.
- Run `uv run pytest` before any live session; gates and sizing have tests.
- Develop with `SAADHAK_LLM=mock` (recorded fixtures). Real calls spend the remaining Featherless credit (about $7); the loop enforces `SAADHAK_LLM_BUDGET_USD` and Book A must keep working with the model switched off.
- Model providers are a config switch. Default to Featherless (the hackathon credit); use Anthropic models only when the user asks for a premium run. Claude Code's subscription may not be used by the running agent.

## Commands
```bash
uv sync
uv run saadhak status
uv run saadhak run --dry-run
uv run pytest
ops/kill.sh          # emergency stop via Alpaca CLI
```

## Stack
Python 3.11 + uv · alpaca-py (Trading + Market Data) · Alpaca MCP server via `uvx alpaca-mcp-server` (stdio) · Alpaca CLI (`brew install alpacahq/tap/cli`) · a Featherless model free on Featherless (`https://Featherless/v1`) for routine cycles (paced, Featherless fallback) · Featherless for a Featherless model catalyst decisions and the gpt-oss-120b adversary with an optional Anthropic adapter behind `PRACTITIONER_PROVIDER` · Streamlit dashboard.
