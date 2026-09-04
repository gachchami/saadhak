# Saadhak — user stories

*Draft v0 (design-time). Add evidence links (dashboard section, journal file, video timestamp) as they exist.*

## Personas
- **Operator (Dhaval)** — runs the agent, must be able to trust it unattended and stop it instantly.
- **Judge (Alpaca / lablab)** — has five minutes per project; wants to see real Alpaca usage, real trades, real reasoning, and a P&L they can verify against the account ID.
- **Follower** — sees a post on X or LinkedIn and wants to understand the idea in one image.
- **Contributor** — clones the repo after the hackathon and wants to run it in dry-run mode.

## Stories

### Operator
1. As the operator, I can start the agent with one command and see within a minute that it reads the account, the clock, and an options chain, so I know credentials and data work. *Accept: `saadhak status` shows equity, next entry window, and at least five SPY contracts with deltas.*
2. As the operator, I can run the whole loop in dry-run mode and see the exact order bodies it would send, so I can review them before real paper money is used. *Accept: `saadhak run --dry-run` journals `order_submitted` records with `dry_run: true` and never calls `POST /v2/orders`.*
3. As the operator, I can stop everything with one script even if the agent process is hung. *Accept: `ops/kill.sh` leaves zero open orders and zero positions, verified by `alpaca position list`.*
4. As the operator, I can leave it unattended, knowing losses are capped per structure, per day, and in total. *Accept: gates 4–6 have unit tests; a simulated 3% daily loss halts new entries.*
5. As the operator, I get a daily markdown report I can paste into a post. *Accept: `saadhak report` prints P&L, trade count, refusal count, Brier score.*

### Judge
6. As a judge, I can open the dashboard and see the equity curve, open structures, and the last ten decisions with their reasons, without logging in. *Accept: public Streamlit URL, loads in under five seconds, no secrets.*
7. As a judge, I can see that the model cannot place orders, as a matter of configuration rather than prompt. *Accept: README and video show the MCP server started with a toolset that excludes trading; the journal lists MCP tools called per cycle.*
8. As a judge, I can see every gate that fired and why a trade was refused. *Accept: `gate_result` records with human-readable reasons; a refusals table on the dashboard.*
9. As a judge, I can see the Alpaca CLI doing real work, not decoration. *Accept: reconciliation records with `source: "alpaca-cli"`; the kill switch and EOD report scripts in the video.*
10. As a judge, I can verify P&L against the account ID in the submission. *Accept: account ID in the form, write-up, and README; portfolio-history chart matches.*
11. As a judge, I can see the original idea working: sizing changed because calibration changed. *Accept: at least one journal entry where `multiplier` differs from the previous cycle and the order quantity followed.*

### Follower
12. As a follower, I understand the idea from one image. *Accept: the architecture sketch (post 1) and the calibration gauge (post 3) each carry a one-sentence caption that stands alone.*

### Contributor
13. As a contributor, I can run the tests and the dry-run loop from a clean clone in under ten minutes. *Accept: `uv sync && uv run pytest && uv run saadhak run --dry-run` works with only the paper keys set.*
14. As a contributor, I can add a new structure type by implementing one builder and one gate profile. *Accept: `engine/structures.py` has a registry; README explains the two-file change.*

## Mapping to judging criteria
| Criterion | Stories |
|---|---|
| P&L Performance | 4, 10 |
| Technology Implementation | 1, 7, 9 |
| Creativity & Originality | 7, 11 |
| Presentation & Execution | 6, 8, 12, 13 |
| Social engagement | 5, 12 |
