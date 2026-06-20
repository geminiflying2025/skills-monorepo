#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from zoneinfo import ZoneInfo


BASE_URL = "https://www.edgevix.com/beacon-api"
ACCESS_KEY_ENV = "BEACON_ACCESS_KEY"
TIME_ZONE = "Asia/Shanghai"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILES = (Path.cwd() / ".env", SKILL_DIR / ".env")


def parse_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].lstrip()
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if key:
            values[key] = parse_env_value(raw_value)
    return values


def resolve_access_key(env_files: Optional[Iterable[Path]] = None) -> str:
    env_value = os.environ.get(ACCESS_KEY_ENV, "").strip()
    if env_value:
        return env_value

    for env_file in env_files if env_files is not None else DEFAULT_ENV_FILES:
        file_value = load_env_file(Path(env_file)).get(ACCESS_KEY_ENV, "").strip()
        if file_value:
            return file_value

    raise RuntimeError(
        f"{ACCESS_KEY_ENV} is not configured. Set it in the environment, "
        "the current directory .env, or the skill .env file."
    )


def build_payload(status: str, title: Optional[str] = None) -> dict[str, str]:
    now = datetime.now(ZoneInfo(TIME_ZONE)).isoformat(timespec="seconds")
    return {
        "title": title or "Codex execution status",
        "body": status,
        "deadline": now,
        "anchor_timezone": TIME_ZONE,
        "mode": "normal",
        "kind": "post_result",
        "source_name": "Codex",
    }


def post_reminder(payload: dict[str, str], access_key: str, timeout: int) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}/reminders",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {
                "status": response.status,
                "response": json.loads(body) if body else None,
            }
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Beacon API returned HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Beacon API request failed: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a Beacon reminder containing the current execution status."
    )
    parser.add_argument("status", help="Current execution status to notify the user about.")
    parser.add_argument("--title", help="Optional reminder title.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload without sending a Beacon notification.",
    )
    args = parser.parse_args()

    payload = build_payload(args.status, args.title)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "payload": payload}, ensure_ascii=False, indent=2))
        return 0

    result = post_reminder(payload, resolve_access_key(), args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
