# Saadhak — the calibrated options agent

**Alpaca paper account: PA36JVGLDYR4 · `8e02ddcf-e8fd-4b5f-9d67-9c619b0334c9`**

Most AI trading agents are confident. Saadhak is calibrated. It states a
probability with every decision, is scored on those probabilities, and is allowed
to risk money in proportion to how well it has actually known what it knows.

## The AI logic

Three roles, each with a boundary enforced by the process rather than by a prompt.

**The engine proposes nothing and decides everything mechanical.** It searches
every combination of expiry, strike distance and wing width on the live chain,
seventy per underlying, and scores each by expected value per dollar at risk. The
probability comes from option deltas, which is the market's own estimate of
finishing in the money.

**The practitioner reviews and may only refuse.** An open-weight model running on
Featherless researches through Alpaca's MCP server and judges the structure the
gates have already accepted. It cannot choose a strike, change a size, or cause a
trade the gates refused: the verdict object has no field through which it could,
and that is asserted in a test. The worst a hallucinating or compromised model
can do is stop us trading. A veto without a stated reason is discarded.

**The witness scores and can only halt.** It reconciles broker state through the
Alpaca CLI against the engine's own REST view — deliberately a different client,
because a checker sharing its subject's code path can only confirm its subject's
mistakes. It also resolves the practitioner's probability statements against what
happened and scores them with a Brier score.

**That score sets position size.** A model claiming 90% and right half the time
is named overconfident and has its budget cut. Crucially the engine sets the
price band and the model states only the probability: allowed to choose both, it
widened bands to 3.3% of price against a 0.6% typical daily move, went eight for
eight, and earned full size by being accurate and useless. On the fixed question
it scores 0.221, which buys 0.76x size rather than 1.00x. A worse number and a
truer one.

During the 17.5 hours a day the options market is shut, the agent forecasts past
sessions it has not seen and is scored on them, with its own record fed back so a
systematic lean has something to correct against.

## The risk gates

Seventeen, evaluated on every candidate, each returning a readable reason that is
journalled whether it passes or fails. The load-bearing ones:

- **Defined risk only.** Every order is a multi-leg limit order with all legs
  covered inside it. No naked shorts, no market orders, ever.
- **Expectancy, not a guessed floor.** With take-profit at half the credit and a
  stop at twice it, breakeven is exactly a 2-in-3 win rate. Gate 8 asks whether
  the structure clears that. The credit floor it replaced was a number chosen by
  feel that refused every trade on the live surface.
- **Sizing** caps loss per structure at 1.5% of equity, scaled by the calibration
  multiplier, with portfolio risk capped at 6%.
- **Event guard.** Earnings are a gap, and gate 8's delta arithmetic assumes
  prices diffuse. Any name reporting inside the holding window is refused, while
  one that has already reported is allowed, because the gap is then behind us.
- **Halts** at 3% daily loss and 6% drawdown, plus a `STOP` file and a CLI kill
  switch. Exits keep running when halted; only entries stop.
- **Idempotent orders**, so a retry can never double-fill.

The gates audit themselves. Gate 8 is derived from measurement, so any hand-picked
gate that repeatedly refuses what gate 8 approved is substituting a guess for a
measurement, and that is countable. Running it found gate 7 rejecting executable
condors by demanding a bid on the far wing, which is bought at the ask and
routinely has none.

## The Alpaca implementation

- **Trading API** — multi-leg (`mleg`) limit orders, positions, portfolio history,
  clock and calendar. Limit prices are signed: negative for credit. Sending a
  positive number silently means "willing to pay this much".
- **Market Data API** — option chain snapshots, stock bars and quotes, news. Greeks
  are absent on same-day contracts on the free feed, so the agent solves implied
  volatility by bisection and computes its own, matching Alpaca's published greeks
  to within 0.01 on contracts where both exist.
- **MCP server** — the practitioner is a real MCP client over stdio, started with
  research toolsets only. Of the 33 tools it can reach, none mutates anything.
- **CLI** — the witness's reconciliation, the kill switch, health checks, and the
  end-of-day report. Order bodies were validated against `--dry-run` before any
  real order was sent.

## What this rests on, and what it does not prove

The account is on Alpaca's free data tier: IEX stock quotes rather than the
consolidated NBBO, indicative option quotes because OPRA is unsigned, and
consolidated data delayed fifteen minutes. Every decision records which feeds
produced it, the age of the worst quote, and whether the inputs should be trusted.
On 2 September a stock moved 8% between our last visible print and the truth.
Trading was never exposed, because the gates only fire during regular hours, but
no conclusion drawn after the close should be believed.

The sample is small. Two sessions of live trading is not evidence that a strategy
works, and the calibration rests on tens of forecasts, not thousands. What the
project demonstrates is a mechanism: an agent that measures its own judgement and
lets the measurement, rather than its confidence, decide how much it may risk.
