#!/usr/bin/env bash
# End-of-day markdown for the daily build-in-public post.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export ALPACA_API_KEY="$APCA_API_KEY_ID" ALPACA_SECRET_KEY="$APCA_API_SECRET_KEY"
echo "### Saadhak — $(date +%Y-%m-%d)"
echo
echo '```'
alpaca account get --jq '{equity, last_equity, cash}'
echo '```'
echo
echo "Positions:"
echo '```'
alpaca position list --jq '[.[] | {symbol, qty, unrealized_pl}]'
echo '```'
uv run saadhak report
