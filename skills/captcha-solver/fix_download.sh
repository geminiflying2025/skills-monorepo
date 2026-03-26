#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source .venv/bin/activate

BASE_URL="https://www.kanyanbao.com/new/view/report/download_check.jsp"
REDIRECT_PATH="${1:-}"

TARGET_URL="$BASE_URL?redirect_url="
if [[ -n "$REDIRECT_PATH" ]]; then
  if [[ "$REDIRECT_PATH" == http://* || "$REDIRECT_PATH" == https://* ]]; then
    TARGET_URL="$REDIRECT_PATH"
  else
    TARGET_URL="${BASE_URL}?redirect_url=${REDIRECT_PATH}"
  fi
fi

python run.py \
  --url "$TARGET_URL" \
  --captcha-image "img#qrcode" \
  --captcha-input "input#j_captcha_response" \
  --submit-button "a#form_post_button" \
  --refresh-button "img#qrcode" \
  --expected-length 4 \
  --max-attempts 3
