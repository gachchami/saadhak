#!/usr/bin/env bash
# Emergency stop: cancel every order, close every position, via the Alpaca CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export ALPACA_API_KEY="$APCA_API_KEY_ID" ALPACA_SECRET_KEY="$APCA_API_SECRET_KEY"
touch STOP
echo "STOP file created; the loop halts at its next cycle."
alpaca order cancel-all --quiet || true
alpaca position close-all --quiet || true
echo "--- remaining ---"
alpaca position list --jq 'length' || true
alpaca order list --status open --jq 'length' || true
