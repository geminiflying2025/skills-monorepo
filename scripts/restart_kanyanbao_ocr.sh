#!/usr/bin/env bash

set -euo pipefail

SERVICE_LABEL="com.macmini.kanyanbao-ocr"
PLIST_PATH="/Users/macmini/Library/LaunchAgents/${SERVICE_LABEL}.plist"
GUI_DOMAIN="gui/$(id -u)"

launchctl kickstart -k "${GUI_DOMAIN}/${SERVICE_LABEL}"
sleep 1
launchctl print "${GUI_DOMAIN}/${SERVICE_LABEL}" | sed -n '1,40p'
echo "---"
lsof -iTCP:8765 -sTCP:LISTEN || true
echo "---"
tail -n 20 /tmp/kanyanbao-ocr.log 2>/dev/null || true
