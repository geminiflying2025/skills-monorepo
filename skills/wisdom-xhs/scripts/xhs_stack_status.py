#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from mcporter_utils import build_mcporter_command, build_mcporter_env, find_mcporter_config, resolve_mcporter_bin


def run_command(args: list[str], timeout: int = 10, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
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


def extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(text[start : end + 1])
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resolve_global_npm_package(package_name: str) -> str | None:
    npm = shutil.which("npm")
    if not npm:
        return None
    result = run_command([npm, "root", "-g"], timeout=10)
    if not result.get("ok"):
        return None
    package_path = Path(str(result.get("stdout", "")).strip()) / package_name
    if package_path.exists():
        return str(package_path)
    return None


def main() -> None:
    docker = shutil.which("docker")
    mcporter = resolve_mcporter_bin()
    agent_reach = shutil.which("agent-reach")
    mcporter_config = find_mcporter_config()

    def with_mcporter_config(base_args: list[str]) -> list[str]:
        return build_mcporter_command(*base_args)

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
        env=build_mcporter_env(),
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    mcp_list = run_command(
        with_mcporter_config(["list", "xiaohongshu", "--json"]),
        timeout=90,
        env=build_mcporter_env(),
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    login_status = run_command(
        with_mcporter_config(["call", "xiaohongshu.check_login_status", "--timeout", "90000"]),
        timeout=100,
        env=build_mcporter_env(),
    ) if mcporter else {"ok": False, "stdout": "", "stderr": "mcporter not found"}

    config_payload = extract_json_object(str(config_get.get("stdout", "")))
    config_dump = json.dumps(config_payload, ensure_ascii=False)
    config_env = config_payload.get("env") if isinstance(config_payload.get("env"), dict) else {}
    cookies_path = (
        config_env.get("COOKIES_PATH")
        or os.environ.get("COOKIES_PATH")
        or str(Path.home() / "Library" / "Application Support" / "wisdom-xhs" / "cookies-node.json")
    )
    xiaohongshu_mcp_node_path = resolve_global_npm_package("xiaohongshu-mcp-node")

    payload = {
        "agent_reach_installed": bool(agent_reach),
        "mcporter_installed": bool(mcporter),
        "mcporter_config": mcporter_config,
        "xiaohongshu_mcp_node_installed": bool(xiaohongshu_mcp_node_path),
        "xiaohongshu_mcp_node_path": xiaohongshu_mcp_node_path,
        "docker_installed": bool(docker),
        "docker_container_running": container_running,
        "mcporter_server_configured": config_get.get("ok", False),
        "domestic_xiaohongshu_mcp_configured": "xiaohongshu-mcp-node" in config_dump,
        "cookies_path": cookies_path,
        "cookies_file_exists": Path(cookies_path).expanduser().exists(),
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
