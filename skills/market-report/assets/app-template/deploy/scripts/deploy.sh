#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/market-report}
ENV_FILE=${ENV_FILE:-/etc/market-report.env}

cd "$APP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing environment file: $ENV_FILE" >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
npm install
npm run build

install -m 644 deploy/systemd/market-report.service /etc/systemd/system/market-report.service
install -m 644 deploy/nginx/market-report.conf /etc/nginx/conf.d/market-report.conf

systemctl daemon-reload
systemctl enable market-report.service
systemctl restart market-report.service
nginx -t
systemctl reload nginx
