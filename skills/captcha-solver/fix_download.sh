#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="${KANYANBAO_PYTHON_BIN:-python3}"

BASE_URL="https://kanyanbao.com/new/view/report/download_check.jsp"
REDIRECT_PATH="${1:-${CAPTCHA_URL:-}}"

TARGET_URL="$BASE_URL?redirect_url="
if [[ -n "$REDIRECT_PATH" ]]; then
  if [[ "$REDIRECT_PATH" == http://* || "$REDIRECT_PATH" == https://* ]]; then
    TARGET_URL="$REDIRECT_PATH"
  else
    TARGET_URL="${BASE_URL}?redirect_url=${REDIRECT_PATH}"
  fi
fi

EXTRA_ARGS=()
if [[ -n "${DOWNLOAD_OUTPUT_PATH:-}" ]]; then
  EXTRA_ARGS+=(--download-output-path "$DOWNLOAD_OUTPUT_PATH")
fi

cmd=(
  "$PYTHON_BIN"
  run.py
  --url "$TARGET_URL"
  --save-storage-state "/tmp/kanyanbao-state-now.json"
  --captcha-image "img#qrcode"
  --captcha-input "input#j_captcha_response"
  --submit-button "a#form_post_button"
  --refresh-button "img#qrcode"
  --expected-length 4
  --max-attempts 3
)

if [[ "${#EXTRA_ARGS[@]}" -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
fi

"${cmd[@]}"
