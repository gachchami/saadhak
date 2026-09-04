# Saadhak (साधक) — the calibrated options agent

An autonomous, defined-risk options trading agent on Alpaca paper trading, built for the
lablaFeatherless × Alpaca AI Trading Agents Hackathon.

**The model proposes, the discipline decides, and a witness keeps score of how well the model
knows what it knows.** Saadhak states a probability with every thesis; a Brier score over those
probabilities sets how much size the next trade is allowed. The agent has to earn the right to
size up by knowing what it knows.

Three roles, each with a real technical boundary:

| Role | What it is | Hard boundary |
|---|---|---|
| **Niyama** (the discipline) | Deterministic risk engine + order builder | The only code path that can create an order |
| **Saadhak** (the practitioner) | A Featherless model connected as an MCP client to Alpaca's MCP server | Its MCP server is started without the trading toolset, so it *cannot* place an order |
| **Sakshi** (the witness) | Hash-chained journal, calibration scoring, reconciliation via the Alpaca CLI | Never trades; can only halt |

Every order is a defined-risk multi-leg options structure. There are no naked short options and
no market orders. See [PLAN.md](PLAN.md) for the full design.

**Live dashboard: https://saadhak.streamlit.app**

**Slides: `slides/index.html`** (reveal.js) · **PDF: `docs/slides.pdf`** · **Video: `docs/saadhak.mp4`**

## Quickstart

```bash
cp .env.example .env     # add your Alpaca paper keys
uv sync
uv run saadhak status                 # account, clock, chain slice with deltas
uv run saadhak plan --symbol SPY      # build a condor and run the gates, no orders
uv run saadhak run --dry-run          # the full loop, orders printed not sent
ops/kill.sh                           # emergency stop
```

Book A (the deterministic theta book) needs **no language model at all** — it trades on greeks
and the gates alone. The model only adds theses, catalyst trades, and calibration.

MIT licensed. Paper trading only.
