from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_mcporter_config() -> str | None:
    candidates = [
        Path.home() / "config" / "mcporter.json",
        Path.home() / ".mcporter" / "mcporter.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def resolve_mcporter_bin() -> str | None:
    direct = shutil.which("mcporter")
    if direct:
        return direct

    candidates = [
        Path.home() / ".local" / "node" / "bin" / "mcporter",
        Path.home() / ".npm-global" / "bin" / "mcporter",
        Path("/opt/homebrew/bin/mcporter"),
        Path("/usr/local/bin/mcporter"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def resolve_node_bin() -> str | None:
    direct = shutil.which("node")
    if direct:
        return direct

    candidates = [
        Path.home() / ".local" / "node" / "bin" / "node",
        Path.home() / ".npm-global" / "bin" / "node",
        Path("/opt/homebrew/bin/node"),
        Path("/usr/local/bin/node"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def build_mcporter_command(*args: str) -> list[str]:
    mcporter_bin = resolve_mcporter_bin()
    if not mcporter_bin:
        raise FileNotFoundError("mcporter")
    command = [mcporter_bin]
    mcporter_config = find_mcporter_config()
    if mcporter_config:
        command.extend(["--config", mcporter_config])
    command.extend(args)
    return command


def build_mcporter_env() -> dict[str, str]:
    env = os.environ.copy()
    extra_dirs: list[str] = []

    mcporter_bin = resolve_mcporter_bin()
    node_bin = resolve_node_bin()
    if mcporter_bin:
        extra_dirs.append(str(Path(mcporter_bin).parent))
    if node_bin:
        extra_dirs.append(str(Path(node_bin).parent))

    current_path = env.get("PATH", "")
    merged_dirs: list[str] = []
    for item in [*extra_dirs, *current_path.split(":")]:
        if item and item not in merged_dirs:
            merged_dirs.append(item)
    env["PATH"] = ":".join(merged_dirs)
    return env
