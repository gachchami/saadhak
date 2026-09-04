#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export ALPACA_API_KEY="$APCA_API_KEY_ID" ALPACA_SECRET_KEY="$APCA_API_SECRET_KEY"
alpaca clock --jq '{open: .is_open, next: .next_open}'
alpaca account get --jq '{status, equity, options_trading_level}'
