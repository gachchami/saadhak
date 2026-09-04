# Saadhak — an options agent that practices a discipline

*Draft v0 (design-time). Update as the build lands; see `TASK.md`.*

## What it is
Saadhak is an autonomous paper-trading agent on Alpaca that trades **only defined-risk options structures** (iron condors, vertical spreads, and occasionally long straddles/strangles around scheduled events). It runs during US market hours, makes its own decisions, and never asks a human to approve a trade. A human can stop it at any time.

The name is Sanskrit for "practitioner": someone who follows a discipline rather than a hunch.

## How it thinks (in one paragraph)
A language model researches the market through Alpaca's MCP server and writes a short thesis with a probability attached ("I think SPY stays inside this range today, 78%"). A separate piece of ordinary, deterministic code — the rules — turns that thesis into a concrete options structure, checks it against seventeen written rules, sizes it, and places it. A third piece — the witness — records everything in a tamper-evident journal, checks the broker's view against the journal using a completely separate tool (the Alpaca command-line client), and keeps score of how accurate the model's probabilities have been. That accuracy score sets how big the next trade may be.

## The three roles
| Role | Plain-language job | What it is *not allowed* to do |
|---|---|---|
| The rules (Niyama) | Build, check, size, place, and exit trades | Invent a trade idea |
| The practitioner (Saadhak) | Research and propose, with a probability | Place or size an order, or pick a strike. The MCP server it uses is started without the trading tools. |
| The witness (Sakshi) | Journal, reconcile, score calibration | Trade. It can only halt. |

## Two books
- **Book A — Theta discipline.** Same-day or next-day SPY/QQQ iron condors with short strikes around 10-delta, $5 wings, entered at 10:05 and 11:30 ET. Take profit at half the credit, stop at a loss equal to the credit, and always closed by 15:45 ET on expiry day. Max loss per structure 1.5% of the account.
- **Book B — Catalyst practice.** Small event trades (max loss 0.5% of the account) only when a scheduled event is inside the holding window and the market's implied move disagrees with history. During the hackathon: Broadcom earnings (Wed after close) and the August jobs report (Fri 08:30 ET).

## Safety limits you can rely on
- Every order is a multi-leg order with all legs inside it; there is no way to be short an uncovered option.
- Daily loss of 3% stops new entries; total drawdown of 6% flattens everything.
- `ops/kill.sh` cancels every order and closes every position through the Alpaca CLI; a file named `STOP` in the repo root does the same at the next cycle.

## Running it (planned)
```bash
cp .env.example .env        # fill APCA_API_KEY_ID / APCA_API_SECRET_KEY (paper), FEATHERLESS_API_KEY (ANTHROPIC_API_KEY only for a premium run)
uv sync
uv run saadhak status       # account, clock, a slice of the SPY chain with deltas
uv run saadhak run --dry-run   # full loop, orders printed instead of sent
uv run saadhak run          # live paper trading
uv run saadhak report       # today's P&L, trades, refusals, calibration
ops/kill.sh                 # emergency stop
```
The dashboard runs on Streamlit Community Cloud and reads the committed journal, so it needs no keys.

## Reading the dashboard (planned sections)
1. **Equity** — account value since Aug 28 from Alpaca's portfolio history.
2. **Open structures** — each with max loss, current P&L, and the exit rule that will fire next.
3. **Decisions** — every cycle: thesis, probability, adversary's objection, which gates passed or failed, what happened.
4. **Calibration** — Brier score over the last 40 resolved forecasts and the sizing multiplier it produces.
5. **Witness** — last reconciliation time and result; hash of the latest journal entry.

## What the numbers rest on

This account is on Alpaca's free market-data tier, and that limits what the agent
can see:

- **Stock quotes come from IEX only**, a single exchange, rather than the
  consolidated national best bid and offer that most traders watch.
- **Option quotes come from the "indicative" feed**, because the OPRA agreement
  is not signed on this account. Alpaca describes these as modified quotes with
  delayed trades.
- **Consolidated data is delayed fifteen minutes.**
- **Greeks are frequently absent** on same-day contracts, so the agent computes
  its own from the quoted prices.

On liquid index products during regular hours this is close enough to trade on,
and every gate that matters only fires while the market is open. It is not close
enough to be quiet about. On 2 September, Broadcom fell to $344 and recovered to
$373 during its earnings call, and the freshest price the agent could see was
sixteen minutes stale and on the wrong side of that reversal.

So every decision records the provenance of its inputs: which feeds, the age of
the worst quote, and whether the market was open. A decision marked `degraded`
was made on inputs that cannot be relied upon, and the journal says so rather
than leaving a reader to assume.

## Glossary
- **Iron condor** — sell a put spread below the market and a call spread above it; profits if the price stays between the short strikes.
- **Vertical (credit/debit) spread** — buy one option and sell another of the same type and expiry at a different strike; risk is capped at the width between strikes.
- **Delta** — roughly, the probability an option finishes in the money; a 10-delta short strike is far from the current price.
- **DTE** — days to expiry. 0 DTE means the option expires today.
- **Brier score** — average squared error of stated probabilities; 0 is perfect, 0.25 is coin-flip guessing.
- **mleg** — Alpaca's multi-leg order class; one order carrying up to four option legs.
- **MCP** — Model Context Protocol; the way the language model calls Alpaca's tools.
