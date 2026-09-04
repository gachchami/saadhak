# lablaFeatherless submission — ready to paste

**Title**
Saadhak — the calibrated options agent

**Short description**
An autonomous Alpaca options agent that earns its position size by proving it knows
what it knows. A language model researching through Alpaca's MCP server may only
veto; nineteen deterministic gates decide; a witness scores every probability the
model states and reconciles the broker through the Alpaca CLI. Defined-risk options
only, no naked shorts, no market orders.

**Long description** — `docs/long-description.txt` (fits the 2000-char limit)

**Tags**
Alpaca · Claude Code · Streamlit · Python · Options · AI Agents · MCP

**Alpaca paper trading account ID**
8e02ddcf-e8fd-4b5f-9d67-9c619b0334c9   (PA36JVGLDYR4)

**Public GitHub repository**
https://github.com/gachchami/saadhak

**Cover image**  docs/cover.png  (1920x1080, 16:9)
**Video**        docs/saadhak.mp4  (3:04, under the 5-minute limit)
**Slides**       docs/slides.pdf (11 pages, the mandatory PDF)
**Slides, web**  slides/index.html — reveal.js deck, same content, keyboard-navigable
**Application URL**  https://saadhak.streamlit.app

## Deployed
https://saadhak.streamlit.app — live, no secrets, reads committed JSON only.
Redeploys automatically on every push to main.

## Results as submitted
- Equity $99,212.36 from a $100,000 start (-0.79%)
- Every loss capped at exactly one credit; no structure exceeded its stated maximum
- 4 structures traded, 3 stopped out, 1 cancelled unfilled
- Calibration: Brier 0.248 over 40 scored forecasts, stating 48% and right 57%
- 159 tests, 30 commits
