#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def find_mcporter_config() -> str | None:
    candidates = [
        Path.home() / "config" / "mcporter.json",
        Path.home() / ".mcporter" / "mcporter.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def run_command(args: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }


def main() -> None:
    docker = shutil.which("docker")
    mcporter = shutil.which("mcporter")
    agent_reach = shutil.which("agent-reach")
    mcporter_config = find_mcporter_config()

    def with_mcporter_config(base_args: list[str]) -> list[str]:
        if mcporter_config:
            return ["mcporter", "--config", mcporter_config, *base_args]
        return ["mcporter", *base_args]

    docker_ps = run_command(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        timeout=10,
    ) if docker else {"ok": False, "stdout": "", "stderr": "docker not found"}

    container_running = False
    if docker_ps.get("ok"):
        container_running = any(
            line.startswith("xiaohongshu-mcp\t")
            for line in docker_ps.get("stdout", "").splitlines()
        )

    config_get = run_command(
        with_mcporter_config(["config", "get", "xiaohongshu", "--json"]),
        timeout=10,
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    mcp_list = run_command(
        with_mcporter_config(["list", "xiaohongshu", "--json"]),
        timeout=20,
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    login_status = run_command(
        with_mcporter_config(["call", "xiaohongshu.check_login_status"]),
        timeout=20,
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    payload = {
        "agent_reach_installed": bool(agent_reach),
        "mcporter_installed": bool(mcporter),
        "mcporter_config": mcporter_config,
        "docker_installed": bool(docker),
        "docker_container_running": container_running,
        "mcporter_server_configured": config_get.get("ok", False),
        "mcp_connected": '"status": "ok"' in mcp_list.get("stdout", "") or '"status":"ok"' in mcp_list.get("stdout", ""),
        "login_status": login_status.get("stdout", "") or login_status.get("stderr", ""),
        "details": {
            "config_get": config_get,
            "mcp_list": mcp_list,
            "login_status": login_status,
        },
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
