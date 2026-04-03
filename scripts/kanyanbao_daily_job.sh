#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${KANYANBAO_PYTHON_BIN:-python3}"
SEARCH_DOWNLOAD_SCRIPT="${KANYANBAO_SEARCH_DOWNLOAD_SCRIPT:-$ROOT_DIR/scripts/kanyanbao_search_download.py}"
REFRESH_STATE_SCRIPT="${KANYANBAO_REFRESH_STATE_SCRIPT:-$ROOT_DIR/scripts/kanyanbao_refresh_state.sh}"
STATE_FILE="${KANYANBAO_STATE_FILE:-/tmp/kanyanbao-state-now.json}"
TIMEZONE_NAME="${KANYANBAO_TIMEZONE:-Asia/Shanghai}"
COLUMN_PRESET="${KANYANBAO_COLUMN_PRESET:-default}"
MIN_PAGES="${KANYANBAO_MIN_PAGES:-5}"
TOP_N="${KANYANBAO_TOP:-1000}"
ALLOW_INTERACTIVE_REFRESH="${KANYANBAO_ALLOW_INTERACTIVE_REFRESH:-0}"

if [[ -n "${KANYANBAO_YESTERDAY:-}" ]]; then
  YESTERDAY="${KANYANBAO_YESTERDAY}"
else
  YESTERDAY="$(
    "$PYTHON_BIN" - <<PY
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("${TIMEZONE_NAME}"))
print((now - timedelta(days=1)).date().isoformat())
PY
  )"
fi

REFRESH_COMMAND=""
if [[ "$ALLOW_INTERACTIVE_REFRESH" == "1" ]]; then
  REFRESH_COMMAND="$REFRESH_STATE_SCRIPT"
fi

exec "$PYTHON_BIN" "$SEARCH_DOWNLOAD_SCRIPT" \
  --column "$COLUMN_PRESET" \
  --min-pages "$MIN_PAGES" \
  --start "$YESTERDAY" \
  --end "$YESTERDAY" \
  --state-file "$STATE_FILE" \
  --top "$TOP_N" \
  --refresh-state-command "$REFRESH_COMMAND"
