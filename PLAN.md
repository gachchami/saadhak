# Saadhak — Build Plan for the Alpaca AI Trading Agents Hackathon

> **Saadhak** (साधक): "the practitioner" — one who follows a discipline (sādhanā) rather than a hunch.
> An autonomous, defined-risk options agent on Alpaca where **the model proposes, the discipline decides, and a witness keeps score of how well the model knows what it knows.**

Written: Wed 2 Sep 2026, 12:15 IST. Submission deadline: **Fri 4 Sep 2026, 20:30 IST (15:00 UTC)**. That is ~56 hours, containing two full US sessions (Wed, Thu) and the first 90 minutes of Friday.

---

## 0. What we verified today (facts the plan is built on)

| Item | Finding |
|---|---|
| Paper account in `.env` | ID `8e02ddcf-e8fd-4b5f-9d67-9c619b0334c9`, number `PA36JVGLDYR4`, created **2026-08-28 15:49 UTC** (49 min after kickoff), equity **$100,000.00**, zero orders, zero positions, options level **3**, 4x margin, options BP $100k. It already satisfies the "fresh, $100k, dedicated" rule. |
| Contest requirements | Autonomous agent on Alpaca Trading API; must use **MCP server or CLI** (we use both); **options mandatory**; paper env; fresh $100k account; **one-page write-up** (AI logic, risk gates, Alpaca infra); public GitHub repo (MIT); video ≤5 min MP4; slides PDF; demo URL on Streamlit/Replit/Vercel; cover 16:9; up to 5 social posts tagging @lablabai and @AlpacaHQ. |
| Judging axes | P&L Performance · Technology Implementation · Creativity & Originality · Presentation & Execution · Social engagement (separate 2×$500 prize). No weights published; judges are Alpaca staff (CBO, Trading API lead, PM, content marketing) plus lablab CEO. |
| Prizes | $2,500 (+$300 Featherless credits), $1,500, $1,000; social 2×$500 + Algo Trader Plus. Featherless integration required for partner-prize eligibility. |
| Market data on this account | Options snapshots on the **indicative** feed work (OPRA not signed). Greeks + IV are present for liquid near-the-money contracts (e.g. SPY 4-Sep 760P: IV 17.0%, delta −0.42, theta −0.90) but **missing for far-OTM contracts** → we compute our own Black-Scholes greeks as fallback. Stock quotes via IEX feed. News API works. |
| Expirations available | SPY / QQQ / IWM have **daily** expirations (Sep 2, 3, 4). AVGO, AAPL, NVDA, TSLA have Sep 2 and Sep 4. Contracts are plentiful (SPY: 330 / 362 / 490 for Sep 2 / 3 / 4). |
| Paper fill model | Orders fill when marketable against NBBO; 10% random partial fills; no slippage model. Options: limit orders at mid generally fill in paper when the quote crosses. mleg orders are limit-only (`order_class: "mleg"`, ≤4 legs, all legs covered, no equity legs). |
| Calendar | Sessions Wed/Thu/Fri 09:30–16:00 ET (19:00–01:30 IST). Deadline = 11:00 ET Friday. |
| Catalysts inside the window | **Broadcom (AVGO) earnings after close today (Wed Sep 2)** — verify on Nasdaq calendar before relying on it. **August jobs report Fri Sep 4, 08:30 ET (18:00 IST)**, one hour before the open, 2.5 hours before the deadline. |
| Local toolchain | Python 3.11.7, uv 0.9.30, Node 26, Docker, gh 2.97. **Alpaca CLI 0.0.14 installed** (`brew install alpacahq/tap/cli`) and authenticated via env vars (`alpaca doctor` passes). `alpaca-mcp-server 2.3.1` runs via `uvx`. `alpaca-py 0.44.0`, `mcp 2.1.1` available on PyPI. |
| Featherless | OpenAI-compatible at `https://api.featherless.ai/v1`. Good agent models: `moonshotai/Kimi-K2.6`, `a Featherless model`, `Qwen/Qwen3-235B-A22B`, `openai/gpt-oss-120b`. $25 credit per participant, first-come-first-served (claim on the hackathon page). |
| Models | **Execution runs on Featherless** (OpenAI-compatible; **$7 of credit remaining**; prices verified from the API) plus **Featherless** (`https://Featherless/v1`, OpenAI Chat Completions compatible, verified on docs.Featherless): the routine 30-minute cycles and micro-forecasts run `a Featherless model` there, where the API is **currently billed at 0 credits** (an active free offer with no published end date; function calling and JSON output supported; 1M context; thinking is always on, so the client sets `reasoning_effort: "low"` for speed). Rate limits are not documented, so the client paces itself and falls back automatically to `a Featherless model` on Featherless at $0.15 / $0.50 on a 429 or quota error; `moonshotai/Kimi-K2.6` ($0.77 / $3.50) only for the two-per-day Book B catalyst decisions; `openai/gpt-oss-120b` ($0.10 / $0.55) as the adversary, a different model family so the disagreement is real. Anthropic is an optional upgrade behind a config switch (`claude-opus-5` at $5/$25 per MTok for a premium run; `claude-haiku-4-5` at $1/$5 as the cheap overflow fallback). Claude Code on the subscription is used for planning and building only: Anthropic's Agent SDK docs disallow claude.ai login for autonomous agents, so the running agent cannot ride on the subscription. |

---

## 0.5 Status against this plan — reviewed 3 Sep 00:55 IST

This section exists because the plan was written once and then not consulted, and
Book B silently slipped. A plan nobody re-reads is a wish. Update this table at
every session boundary.

| Component | Planned | Actual | Note |
|---|---|---|---|
| Broker layer, greeks fallback | Wed 12:30–13:30 | **done** | Alpaca omits greeks on 0DTE; our Black-Scholes fallback carries strike selection |
| Structures, sizing, 17 gates, journal | Wed 13:30–17:30 | **done** | gate 8 later replaced by a derived expectancy test |
| Loop, monitor, kill switch | Wed 17:30–18:45 | **done** | shipped late, after the first fill rather than before |
| First live trade | Wed 19:00 | **done 19:36** | SPY condor, 11 contracts, $165 credit |
| Practitioner (MCP + model) | Wed 19:35–22:30 | **done, late** | slipped to Thu 00:55 |
| Adversary (second model arguing the opposite) | Wed 22:30–00:00 | **NOT BUILT** | dropped |
| **Book B — catalyst trading** | Wed 22:30–00:00 | **NOT BUILT** | the AVGO earnings window passed unused |
| **Calibration scoring → sizing** | Thu 09:00–11:30 | **NOT BUILT** | this is the project's headline claim and it is a stub |
| Reconciliation via CLI | Thu 09:00–11:30 | **NOT BUILT** | gate 16 hardcodes `reconciled=True` |
| Dashboard | Thu 11:30–14:00 | **NOT BUILT** | required: submission needs a demo URL |
| Video, slides, write-up, cover | Fri 09:00–12:00 | **NOT BUILT** | required: no video means no valid submission |
| Social posts | throughout | **NONE POSTED** | separate $500 prize forfeited so far |

### Why Book B was not built

Not a judgement call — nobody made one. Three causes, in order of blame:

1. **No mechanism watched the plan.** I wrote an hour-by-hour schedule and never
   re-read it. The same failure the engine was corrected for: a decision that
   lives in someone's memory instead of in a system that checks.
2. **Interrupt-driven work.** Each question surfaced a genuine defect — a time
   stop that would have destroyed a winning expiry, a practitioner that failed
   open on an earnings name. Fixing them was right. Returning to the plan
   afterwards never happened.
3. **Dependency order favoured Book A.** Book A was the critical path to any
   trade at all, and it kept earning attention because it was live and losing.

### Revised order for the time that remains

Deadline Fri 4 Sep 20:30 IST. Two sessions left. Ranked by what forfeits the most
if missing:

1. **Submission artifacts** — video, slides, write-up, cover, demo URL. Mandatory;
   without them the work does not count at all.
2. **Calibration scoring** — the headline claim. The practitioner already records
   a probability and a range forecast on every decision; resolving and scoring
   them is what makes "the agent earns its size" true rather than asserted.
3. **Dashboard** — doubles as the demo URL, so it pays for itself twice.
4. **Book B** — one remaining trigger, Friday's jobs report, decided Thursday
   afternoon. Build only if 1–3 are done. It needs its own probability model,
   because gate 8's delta arithmetic cannot price a gap.
5. **Adversary** — cut. It duplicates the practitioner's function at extra cost.


---

## 1. Why this wins: the concept

Fifty-plus submissions are already up. Nearly all of them say the same sentence: "the LLM proposes, deterministic code decides, defined-risk credit spreads, hash-chained audit log, multi-agent debate." That is now table stakes, not originality. We keep the table stakes (they are correct engineering) and add one idea nobody in the pool has made central:

**The agent is sized by its own calibration.** Saadhak states a probability with every thesis. A separate witness process scores those probabilities against outcomes (Brier score) and feeds the score back into position sizing. A model that says "80%" and is right 80% of the time earns full size; a model that says "80%" and is right 55% of the time gets cut to a quarter. The agent literally has to *earn the right to size up by knowing what it knows*. Before it trades at all, it **practices** (sādhanā) on recent history to seed its calibration.

Three roles, each with a real technical boundary — not a prompt:

| Role | Name | What it is | Hard boundary |
|---|---|---|---|
| The discipline | **Niyama** (the rules) | Deterministic risk engine + order builder in Python on `alpaca-py` | The only code path that can create an order. Seventeen numbered gates. |
| The practitioner | **Saadhak** (the LLM) | a Featherless model (free on Featherless, Featherless fallback) for routine cycles and a Featherless model on Featherless for catalyst decisions, connected as a real **MCP client** to the Alpaca MCP server for research; a different model family (gpt-oss-120b) plays the **pūrvapakṣa** (the opposing argument it must answer) | The MCP server it talks to is started with `ALPACA_TOOLSETS=options-data,stock-data,news,account` — **the trading toolset is not loaded**, so the model cannot place an order even if prompted to. It never sees or writes an OCC symbol for an order. |
| The witness | **Sakshi** (the observer) | Separate process: hash-chained journal, calibration scoring, and **independent reconciliation of journal vs. broker state through the Alpaca CLI** | Never trades. Can only halt. Uses a different client (the CLI) than the engine (the SDK) so a bug in one cannot hide in the other. |

Pitch line for the video: *"Most AI trading agents are confident. Saadhak is calibrated."*

---

## 2. Rubric map (what each judge will see)

| Criterion | What we do | Evidence in submission |
|---|---|---|
| **P&L Performance** | Two books, both defined-risk, all options. Book A harvests 0–1 DTE theta on SPY/QQQ with 8–15-delta short strikes, exits at 50% profit / 2× credit / time stop. Book B takes small, catalyst-driven trades (AVGO earnings, jobs report) only when the implied move disagrees with history. Daily loss limit 3%, total 6%. Target stated up-front: **+1–3% on $100k with max drawdown < 3% and zero undefined-risk exposure**. | Live account ID; portfolio-history chart; trade table with every entry/exit reason; refusals table; equity curve in video. |
| **Technology Implementation** | **Trading API** (alpaca-py): mleg limit orders, positions, account, clock/calendar, portfolio history. **Market Data API**: option chain snapshots w/ greeks, stock bars/quotes, news. **MCP server**: the practitioner is an MCP client (Python `mcp` SDK over stdio to `uvx alpaca-mcp-server`) with a restricted toolset. **CLI**: kill switch, EOD report, health check, `--dry-run` order validation in CI, and the Witness's reconciliation. **Featherless**: practitioner (a Featherless model free on Featherless with Featherless fallback; a Featherless model on Featherless for catalysts) and adversary (gpt-oss-120b), schema-validated theses with one retry; an Anthropic adapter sits behind a config switch for a premium run. | Architecture slide; `ops/*.sh` scripts; MCP config with toolsets; a 20-second clip of the CLI reconciling positions. |
| **Creativity & Originality** | Calibration-driven sizing; practice-before-performance; opposing-argument step; the "model cannot trade" enforced by toolset, not prompt; the Witness using a second client for reconciliation. | Calibration gauge on dashboard; a journal entry where the size was cut because Brier drifted; write-up section "How Saadhak earns size". |
| **Presentation & Execution** | 5-minute video with one live cycle end-to-end, a veto, a fill, a reconciliation; 10-slide PDF; one-page write-up; clean README with a 60-second quickstart; Streamlit dashboard reading the public journal. | Video, slides, write-up, dashboard URL, README. |
| **Social engagement** | Five posts (below) over three days, each with a concrete artifact (diagram, veto screenshot, EOD numbers, calibration chart, final results). Tag @lablabai + @AlpacaHQ on X; lablaFeatherless + Alpaca on LinkedIn. | Five links in the submission form. |

---

## 3. Strategy specification

### 3.1 Book A — "Theta discipline" (deterministic core, ~80% of risk budget)
- **Underlyings**: SPY, QQQ (IWM optional if liquidity gate passes).
- **Structure**: iron condor by default; single credit vertical when the practitioner's directional probability > 0.65 and the adversary did not overturn it.
- **Expiry**: 0 DTE (same day) for entries before 11:30 ET; 1 DTE for entries after.
- **Strikes**: short strikes at the contract nearest **10-delta** (bounds 8–15) using Alpaca greeks, fallback to in-house Black-Scholes with IV from the ATM contract. Wings **$5** (SPY/QQQ).
- **Credit floor**: condor credit ≥ 18% of one wing width; vertical ≥ 25%.
- **Entry windows**: 10:05 ET and 11:30 ET (never in the first 15 or last 15 minutes).
- **Sizing**: max loss per structure ≤ 1.5% of equity ($1,500) × calibration multiplier. Example: $5 wings, $1.00 credit → $400 max loss/contract → 3 contracts at full multiplier.
- **Exits** (monitored every 60 s): take profit at 50% of credit; stop at 2× credit (i.e. loss = credit); time stop 15:45 ET on expiry day; **any short strike within 0.3% of spot at 15:30 ET → close** (avoids assignment on ITM short legs; Alpaca auto-exercises ITM at expiry).
- **Portfolio caps**: ≤ 6 open structures; ≤ 2 per underlying; open risk ≤ 6% of equity.

Why this book: with two sessions of P&L, a high-probability, short-dated, defined-risk book gives the smoothest equity curve and the highest chance the account shows green at judging. Paper fills at NBBO help because we are always the passive side at mid.

### 3.2 Book B — "Catalyst practice" (LLM-led, ~20% of risk budget, ≤0.5% max loss per trade)
- **Universe**: AVGO, AAPL, NVDA, MSFT, TSLA, SPY, IWM — liquid only.
- **Trigger**: a scheduled catalyst inside the holding window. Today: **AVGO earnings after close** (decide by 15:00 ET Wed using Sep 4 expiry). Thursday: **jobs report Friday 08:30 ET** (decide at 15:00 ET Thu using SPY/IWM Sep 4 expiry).
- **Method**: engine computes the implied move from the ATM straddle; practitioner researches via MCP (news, chain, snapshots) and returns a thesis with `p_success`; adversary (Featherless) must argue the opposite; practitioner responds; engine picks from the whitelist: iron condor beyond the implied move (if implied > historical), long straddle/strangle (if implied < historical and the practitioner's probability ≥ 0.6), or debit/credit vertical for a directional view, or **pass**.
- **Exits**: 50% profit or 2× loss on credit structures; for long-vol structures close 30 min after the open on the event day.
- Note: any Friday-expiry position will still be open at the 11:00 ET deadline and will be marked-to-market — that is accepted risk, sized at 0.5%.

### 3.3 Micro-forecasts (calibration fuel)
Every practitioner cycle (every 30 min during the session) also records one cheap forecast per underlying: *P(close is within [lo, hi])* for the day. These resolve at 16:00 ET and give ~12 resolved forecasts per underlying per day, so the Brier score becomes meaningful within the first session instead of after 20 trades.

### 3.4 Calibration → size
- `brier = mean((p_i − outcome_i)²)` over resolved forecasts (window: last 40).
- `multiplier = clip(1.0 − 2·(brier − 0.10), 0.25, 1.0)` → Brier 0.10 → 1.0×; 0.25 (coin-flip) → 0.70×; 0.35 → 0.50×; ≥0.475 → 0.25×.
- Prior before any data: Brier 0.30 → 0.60×. `saadhak practice` (Section 5, stretch S1) replays the last 10 sessions to replace the prior with earned data.

---

## 4. The seventeen gates (Niyama) — every order passes all of them or is refused with a reason

1. Market is open; not within the first 15 or last 15 minutes (exits exempt).
2. Underlying on the whitelist for the book.
3. Defined-risk only: every order is `mleg`, all legs covered inside the order, no equity legs, no naked shorts.
4. Max loss per structure ≤ 1.5% (A) / 0.5% (B) of current equity, computed as `width × 100 × qty − credit` (or debit paid).
5. Portfolio open risk ≤ 6% of equity; ≤ 6 structures; ≤ 2 per underlying.
6. Daily loss ≥ 3% → no new entries; total drawdown ≥ 6% → flatten and stop.
7. Liquidity: every leg has bid > 0 and spread ≤ 15% of mid (or ≤ $0.10); day volume ≥ 100 on short legs.
8. Credit/debit floors (condor ≥ 18% width, vertical ≥ 25%, debit ≤ 40%).
9. Short-strike delta within 8–15 (Book A).
10. Days to expiry within bounds (A: 0–1; B: ≤ 7).
11. Event guard: no new 0DTE Book A entry when a scheduled macro release falls inside the holding window (the jobs report is handled by Book B only).
12. Calibration multiplier applied to size; size ≥ 1 contract or refuse.
13. Idempotent orders: `client_order_id = sha256(cycle_id + structure)[:32]`; a retry can never double-fill.
14. Fill discipline: limit at mid; if unfilled after 20 s, step one-third toward the natural price, at most 3 steps, then cancel and journal "unfilled". **Never a market order for options.**
15. Exit rules attached at entry (TP/SL/time/proximity) and enforced by the monitor, not by the model.
16. Reconciliation: the Witness compares broker orders/positions (via the **CLI**) to the journal every 5 min; any mismatch halts new entries and raises an alert.
17. Kill switch: `ops/kill.sh` (CLI: cancel all, close all) and a `STOP` file the loop checks every cycle.

The practitioner's output schema (structured output, validated with Pydantic):

```json
{
  "underlying": "SPY", "book": "A",
  "thesis": "…", "direction": "neutral|up|down|vol_up|vol_down",
  "p_success": 0.78,
  "structure": "iron_condor|put_credit_spread|call_credit_spread|call_debit_spread|put_debit_spread|long_straddle|long_strangle|pass",
  "expiry": "2026-09-02", "short_delta_target": 0.10, "width": 5,
  "evidence": ["…"], "risks": ["…"],
  "adversary_rebuttal": "…", "response_to_adversary": "…",
  "micro_forecast": {"lo": 756.0, "hi": 767.0, "p": 0.72}
}
```
The engine converts this into concrete strikes and legs. The model never chooses a strike or quantity.

---

## 5. Architecture and repo layout

```
saadhak/
├── saadhak/                    # Python package (3.11, uv)
│   ├── config.py               # pydantic-settings; reads .env (APCA_* keys), UTC everywhere
│   ├── broker/                 # alpaca-py wrappers
│   │   ├── account.py          # account, clock, calendar, portfolio history
│   │   ├── data.py             # option chain snapshots (+greeks fallback), stock bars/quotes, news
│   │   └── orders.py           # mleg builder, submit/replace/cancel, fill stepping, positions
│   ├── engine/                 # Niyama
│   │   ├── gates.py            # the 17 gates, each returns (ok, reason)
│   │   ├── structures.py       # condor / vertical / straddle builders from a thesis
│   │   ├── sizing.py           # max-loss math, calibration multiplier
│   │   └── monitor.py          # exit rules every 60 s
│   ├── practitioner/           # Saadhak
│   │   ├── mcp_client.py       # stdio MCP client → uvx alpaca-mcp-server (restricted toolsets)
│   │   ├── llm.py              # OpenAI-compatible client (Featherless) + optional Anthropic adapter; JSON schema + Pydantic retry
│   │   ├── adversary.py        # Featherless (OpenAI-compatible) opposing argument
│   │   └── prompts/            # system prompt, thesis schema, practice prompt
│   ├── witness/                # Sakshi
│   │   ├── journal.py          # append-only JSONL, sha256 hash chain, publishes state/latest.json
│   │   ├── calibration.py      # forecast resolution, Brier, multiplier
│   │   └── reconcile.py        # shells out to `alpaca order list` / `alpaca position list`
│   ├── loop.py                 # scheduler: entry windows, 30-min practitioner cycles, 60-s monitor
│   └── cli.py                  # `saadhak run | status | kill | report | practice`
├── ops/                        # Alpaca CLI scripts
│   ├── kill.sh                 # alpaca order cancel-all && alpaca position close-all
│   ├── eod_report.sh           # positions + portfolio history --jq → markdown for the daily post
│   ├── healthcheck.sh          # alpaca clock + account get; exit codes for cron
│   └── validate_orders.sh      # replays journal orders with --dry-run in CI
├── dashboard/app.py            # Streamlit; reads state/latest.json + journal/*.jsonl from the public repo
├── journal/                    # committed every cycle → the repo is the audit trail
├── state/latest.json           # dashboard contract
├── tests/                      # gates, sizing, structure builders, hash chain, schema
├── docs/                       # write-up.md, slides.pdf, cover.png, video script
├── human-docs/                 # human-facing docs; agents ignore (see CLAUDE.md)
├── .env.example  .gitignore  CLAUDE.md  LICENSE (MIT)  README.md  pyproject.toml  Dockerfile
```

**Runtime**: the loop runs on this Mac under `caffeinate -i` with a launchd plist for auto-restart (fastest); a Dockerfile is provided so the same image can be dropped on Fly.io/Railway by Thursday evening as the durable home for the judging period. The dashboard runs on Streamlit Community Cloud from the public repo and needs no secrets (reads committed journal files).

**Model cost, budgeted against the $7 of Featherless credit that remains**: a compact practitioner cycle (≤ 6 MCP tool calls, the engine pre-filters the chain to ~30 contracts, ≤ 40k cumulative input tokens, ~2.5k output) costs $0 on Featherless (≈ $0.011 if it falls back to Featherless); the adversary turn on gpt-oss-120b adds ≈ $0.005; a Book B catalyst decision on Kimi-K2.6 ≈ $0.06. About 34 routine cycles plus 5 catalyst decisions across the competition ≈ $0.50 of Featherless credit, plus ≈ 15 real development cycles ≈ $0.10 (every other development run uses `SAADHAK_LLM=mock` with recorded fixtures). Expected spend ≈ $0.60 of Featherless credit and $0 on Featherless, and ≈ $1 even if everything falls back to Featherless, so there is room to keep running through the judging week. The client paces requests to the account's rate limit; a cycle's tool loop takes 1–2 minutes, fine at a 30-minute cadence. A hard cap `SAADHAK_LLM_BUDGET_USD=6.00` is metered from the `usage` field of every response and journaled; at the cap the practitioner and adversary switch off and Book A keeps trading deterministically, because it never needs the model. Overflow options: gpt-oss-120b on Featherless at about a tenth of the price, a free-tier OpenAI-compatible host (Groq, Google AI Studio) by base-URL swap, or `claude-haiku-4-5` for ≈ $5–10. A premium run on `claude-opus-5` would be ≈ $40–70. No real capital is at risk; the $100k is paper.

**Stretch items** (only if ahead of schedule): S1 `saadhak practice` (replay last 10 sessions for calibration seed) · S2 FastAPI `/state` `/journal` `/health` endpoints for the dashboard instead of file reads · S3 Telegram alert on halt · S4 IWM in Book A.

---

## 6. Hour-by-hour schedule (IST)

### Wednesday 2 Sep
| Time | Work | Done when |
|---|---|---|
| 12:30–13:30 | Repo scaffold (uv, pyproject, package skeleton, `.env.example`, MIT license), config, `broker/account.py`, `broker/data.py` with greeks fallback | `saadhak status` prints account, clock, SPY chain slice with deltas |
| 13:30–15:30 | `broker/orders.py` mleg builder + fill stepping; `engine/structures.py`; validate bodies with `alpaca order submit --dry-run --order-class mleg --legs …` | A condor body is built from a delta target and passes dry-run |
| 15:30–17:30 | `engine/gates.py` (17 gates) + `sizing.py` + tests; `witness/journal.py` (hash chain) | `pytest` green; refusal reasons are strings a judge can read |
| 17:30–18:45 | `loop.py` + `monitor.py`; `ops/kill.sh`; `STOP` file; launchd plist; **social post #1** (architecture sketch) | Dry-run loop runs through a fake cycle end-to-end |
| **19:00** | **Market opens.** Run Book A on SPY only, 1 contract, watch the 10:05 ET entry (19:35 IST) and monitor | First real mleg fill in the account |
| 19:35–22:30 | `practitioner/mcp_client.py` (restricted toolsets), `llm.py` structured thesis, micro-forecasts; wire into the 30-min cycle | A thesis JSON is journaled with MCP tool calls listed |
| 22:30–00:00 | `adversary.py` (Featherless); Book B; **AVGO decision by 00:30 IST (15:00 ET)** | AVGO trade or documented pass in the journal |
| 00:00–01:30 | Watch exits; time-stop logic verified at 01:15 IST (15:45 ET) | Clean close of 0DTE positions |
| 01:30 | `ops/eod_report.sh` → **social post #2** (EOD numbers + first veto) | Posted |

### Thursday 3 Sep
| Time | Work | Done when |
|---|---|---|
| 09:00–11:30 | `witness/calibration.py` + `reconcile.py` (CLI); calibration multiplier wired into sizing; resolve Wednesday's micro-forecasts | Dashboard-ready `state/latest.json` with Brier + multiplier |
| 11:30–14:00 | Streamlit dashboard (equity, open structures, decisions feed with refusals, calibration gauge, reconciliation status); deploy to Streamlit Cloud | Public URL renders from the repo |
| 14:00–17:00 | README quickstart, one-page write-up draft, slides skeleton, Dockerfile; record B-roll clips (CLI reconcile, MCP toolset config); **social post #3** (calibration gauge) | Draft docs in `docs/` |
| 17:00–18:45 | Bug fixes from Wednesday's journal; QQQ enabled; dry-run the jobs-report Book B path | Tests green |
| **19:00–01:30** | Session 2 live. **Jobs-report structure decision at 00:30 IST (15:00 ET)**. Record the live-cycle screen capture for the video during 19:35–20:30 IST | Second session journaled; video raw footage captured |
| 01:30 | EOD report → **social post #4** | Posted |

### Friday 4 Sep
| Time | Work | Done when |
|---|---|---|
| 09:00–12:00 | Edit video (≤5 min, MP4), finalize slides (PDF), write-up (one page), cover image (16:9 PNG) | Files in `docs/`, uploaded to lablab draft |
| 12:00–14:00 | Final README, tags, short/long descriptions; deploy container to Fly.io/Railway (or confirm the Mac stays up); submission form filled except final numbers | Draft submission complete |
| 18:00 | Jobs report prints; Book B exit rules active at open | — |
| **19:00–19:45** | Session 3 (short). Snapshot equity curve, fill final numbers into slides/write-up | Final numbers in |
| **19:45–20:00** | **Submit** (30-minute buffer before 20:30 deadline). **Social post #5** with results + demo link, add link to submission | Submitted |
| after | Decide: keep Book A running at half size during judging (default) or flatten. `ops/kill.sh` at any time. | — |

---

## 7. Submission checklist

- [ ] Title: **Saadhak — the calibrated options agent**
- [ ] Short description (≤ limit): "An autonomous Alpaca options agent that sizes itself by its own calibration: an open model proposes through the Alpaca MCP server, seventeen deterministic gates decide, and a witness that reconciles through the Alpaca CLI keeps score."
- [ ] Long description: concept, three roles, two books, the 17 gates, calibration math, Alpaca stack usage (Trading API, Market Data, MCP with restricted toolsets, CLI), Featherless adversary, results, what we learned.
- [ ] Tags: Alpaca, Featherless, Claude Code, Streamlit, Python, Options, AI Agents.
- [ ] Cover image 16:9 PNG (calibration gauge + equity curve on dark background).
- [ ] Video MP4 ≤ 5:00 (script in §8).
- [ ] Slides PDF (10 slides, §8).
- [ ] Public GitHub repo with MIT `LICENSE`, `.env` **never** committed, `journal/` committed.
- [ ] Demo platform: Streamlit; Application URL: the Streamlit Cloud app.
- [ ] **Alpaca paper account ID: `8e02ddcf-e8fd-4b5f-9d67-9c619b0334c9` (PA36JVGLDYR4)**.
- [ ] One-page write-up (`docs/write-up.md` → PDF): AI logic · risk gates · Alpaca infrastructure implementation.
- [ ] Up to 5 social links.
- [ ] Featherless credits claimed (first-come) and the model named in the repo.

**Human-only actions** (the agent will not do these for you): claim Featherless credits, create the public GitHub repo (or approve `gh repo create`), post on X/LinkedIn, record voice-over, fill and submit the lablab form, decide the post-deadline run policy.

---

## 8. Presentation assets

**Video script (5:00)**
- 0:00–0:30 Hook: "Most AI trading agents are confident. Saadhak is calibrated." Equity curve + calibration gauge on screen.
- 0:30–1:30 Three roles and their hard boundaries; the MCP config with the trading toolset absent; the CLI kill switch.
- 1:30–3:00 One live cycle: MCP chain/news calls → thesis JSON with p_success → adversary rebuttal → gates (show one veto with its reason) → mleg limit at mid via Trading API → fill → journal hash.
- 3:00–4:00 Results: trades, P&L, refusals, calibration trend and the moment size was cut or restored, Witness reconciling through the CLI.
- 4:00–4:45 Setbacks and what we learned (build in public).
- 4:45–5:00 Account ID, repo, dashboard.

**Slides (10)**: Title · The problem (confidence ≠ calibration) · Concept: sādhanā · Architecture · The 17 gates · The practitioner schema · Calibration → size · Alpaca stack usage (API / Data / MCP / CLI) · Results · Build-in-public, learnings, next.

**Social posts** (each with an image; tag @lablabai @AlpacaHQ on X, lablaFeatherless + Alpaca on LinkedIn):
1. Wed afternoon: architecture sketch — "the model can't place orders, and here's the config line that guarantees it."
2. Wed night: EOD numbers + screenshot of the first veto and its reason.
3. Thu midday: calibration gauge — "how Saadhak earns the right to size up."
4. Thu night: EOD numbers + the CLI reconciliation clip.
5. Fri: final results, dashboard link, repo link.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Indicative feed quotes are modified/delayed → stale mid | Limit at mid with 3-step walk toward natural, then abandon; never market. Log quote age; refuse if > 60 s. |
| Greeks absent on far-OTM contracts | In-house Black-Scholes with IV interpolated from the nearest quoted contracts. |
| Short leg goes ITM near expiry (auto-exercise/assignment) | Gate 15 proximity close at 15:30 ET; time stop 15:45 ET. |
| A single bad session wipes the P&L story | Daily 3% halt, 6% total; Book B capped at 0.5% per trade; open risk ≤ 6%. |
| Jobs-report gap on Friday before the deadline | Only Book B, only sized at 0.5%, structure chosen against the implied move; Book A has no Friday 0DTE entries before 10:05 ET anyway. |
| Duplicate orders on retries | Deterministic `client_order_id` per cycle+structure. |
| Mac sleeps / process dies | `caffeinate -i`, launchd KeepAlive, healthcheck cron via CLI; Docker image ready for Fly.io by Thursday. |
| LLM latency or outage | Cycle has a 90-s budget; on timeout the cycle records "no thesis" and Book A proceeds deterministically (it never depends on the model to exit). |
| Featherless credit ($7) runs out | The $6 budget cap switches the practitioner off and Book A continues deterministically; then gpt-oss-120b, a free-tier host by base-URL swap, or `claude-haiku-4-5` for ≈ $5–10. The journal records which model argued. |
| Featherless free offer ends or rate-limits | Automatic fallback to Featherless a Featherless model (≈ $0.011 per cycle); Featherless on Featherless is a second currently-free model from a different family if needed. |
| Rate limits (200 req/min) | Chain pulls are filtered by expiry and strike range; snapshots batched by symbol list. |
| Time-zone bugs | All internal timestamps UTC; ET only at the scheduler boundary; IST only in docs. |
| Secrets leak in the public repo | `.gitignore` has `.env`; `.env.example` committed; pre-commit grep for `APCA_`. |

---

## 10. Definition of done

1. The account shows ≥ 6 completed defined-risk options structures across Wed/Thu, every one journaled with entry reason, gate results, exit reason, and hash.
2. At least one journaled refusal per gate category that fired, and one size change attributed to calibration.
3. MCP client logs show real tool calls to the Alpaca MCP server with the restricted toolset; CLI scripts run in the video.
4. Dashboard public; repo public with MIT license; tests green; `.env` absent from history.
5. Video, slides, write-up, cover, five posts, account ID — all in the form, submitted by 20:00 IST Friday.
