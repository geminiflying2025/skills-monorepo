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
ALLOW_INTERACTIVE_REFRESH="${KANYANBAO_ALLOW_INTERACTIVE_REFRESH:-1}"

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

OUTPUT_DIR="${KANYANBAO_OUTPUT_DIR:-$ROOT_DIR/output/kanyanbao-${YESTERDAY}_to_${YESTERDAY}}"
MANIFEST_JSON="$OUTPUT_DIR/download_manifest.json"

REFRESH_COMMAND=""
if [[ "$ALLOW_INTERACTIVE_REFRESH" != "0" ]]; then
  REFRESH_COMMAND="$REFRESH_STATE_SCRIPT"
fi

extract_summary() {
  local stdout_file="$1"
  "$PYTHON_BIN" - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
decoder = json.JSONDecoder()
best = None
for idx, ch in enumerate(text):
    if ch != "{":
        continue
    try:
        obj, end = decoder.raw_decode(text[idx:])
    except json.JSONDecodeError:
        continue
    if isinstance(obj, dict):
        best = obj
if best is None:
    raise SystemExit("no json summary found in stdout")
print(json.dumps(best, ensure_ascii=False))
PY
}

count_failed_rows() {
  local manifest_path="$1"
  "$PYTHON_BIN" - "$manifest_path" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print(0)
    raise SystemExit
data = json.loads(path.read_text(encoding="utf-8"))
print(sum(1 for row in data if not row.get("ok")))
PY
}

merge_retry_manifest() {
  local original_manifest="$1"
  local retried_manifest="$2"
  local output_manifest="$3"
  "$PYTHON_BIN" - "$original_manifest" "$retried_manifest" "$output_manifest" <<'PY'
import csv
import json
import sys
from pathlib import Path

orig_path = Path(sys.argv[1])
retry_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])
csv_path = output_path.with_suffix(".csv")

orig_rows = json.loads(orig_path.read_text(encoding="utf-8"))
retry_rows = json.loads(retry_path.read_text(encoding="utf-8"))
retry_by_key = {
    (row.get("objid"), row.get("file")): row
    for row in retry_rows
}

merged = []
for row in orig_rows:
    key = (row.get("objid"), row.get("file"))
    merged.append(retry_by_key.get(key, row))

output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["index", "report_id", "objid", "title", "file", "url", "ok", "status", "error"],
    )
    writer.writeheader()
    writer.writerows(merged)

summary = {
    "matched": len(merged),
    "downloaded_ok": sum(1 for row in merged if row.get("ok")),
    "download_failed": sum(1 for row in merged if not row.get("ok")),
    "manifest_json": str(output_path),
    "manifest_csv": str(csv_path),
}
print(json.dumps(summary, ensure_ascii=False))
PY
}

run_search() {
  local stdout_file="$1"
  shift
  if "$PYTHON_BIN" "$SEARCH_DOWNLOAD_SCRIPT" "$@" >"$stdout_file"; then
    cat "$stdout_file" >&2
    return 0
  fi
  local rc=$?
  cat "$stdout_file" >&2
  return "$rc"
}

first_stdout="$(mktemp /tmp/kanyanbao-daily-first-XXXXXX.log)"
retry_stdout=""
original_manifest_copy=""
cleanup() {
  rm -f "$first_stdout"
  if [[ -n "$retry_stdout" ]]; then
    rm -f "$retry_stdout"
  fi
  if [[ -n "$original_manifest_copy" ]]; then
    rm -f "$original_manifest_copy"
  fi
}
trap cleanup EXIT

base_args=(
  --column "$COLUMN_PRESET"
  --min-pages "$MIN_PAGES"
  --start "$YESTERDAY"
  --end "$YESTERDAY"
  --state-file "$STATE_FILE"
  --top "$TOP_N"
  --refresh-state-command "$REFRESH_COMMAND"
  --output-dir "$OUTPUT_DIR"
)

run_search "$first_stdout" "${base_args[@]}"
first_summary_json="$(extract_summary "$first_stdout")"
failed_count="$(count_failed_rows "$MANIFEST_JSON")"

if [[ "$failed_count" -eq 0 ]]; then
  printf '%s\n' "$first_summary_json"
  exit 0
fi

original_manifest_copy="$(mktemp /tmp/kanyanbao-retry-source-XXXXXX.json)"
cp "$MANIFEST_JSON" "$original_manifest_copy"

retry_stdout="$(mktemp /tmp/kanyanbao-daily-retry-XXXXXX.log)"
run_search "$retry_stdout" \
  --state-file "$STATE_FILE" \
  --refresh-state-command "$REFRESH_COMMAND" \
  --retry-failed-manifest "$original_manifest_copy" \
  --output-dir "$OUTPUT_DIR"
retry_summary_json="$(extract_summary "$retry_stdout")"

merged_summary_json="$(merge_retry_manifest "$original_manifest_copy" "$MANIFEST_JSON" "$MANIFEST_JSON")"
final_summary_json="$(
  "$PYTHON_BIN" - "$first_summary_json" "$retry_summary_json" "$merged_summary_json" <<'PY'
import json
import sys

first = json.loads(sys.argv[1])
retry = json.loads(sys.argv[2])
merged = json.loads(sys.argv[3])

first["matched"] = merged["matched"]
first["downloaded_ok"] = merged["downloaded_ok"]
first["download_failed"] = merged["download_failed"]
first["manifest_json"] = merged["manifest_json"]
first["manifest_csv"] = merged["manifest_csv"]
first["retried_failed_count"] = retry["matched"]
first["retried_downloaded_ok"] = retry["downloaded_ok"]
first["retried_download_failed"] = retry["download_failed"]
print(json.dumps(first, ensure_ascii=False))
PY
)"

printf '%s\n' "$final_summary_json"
