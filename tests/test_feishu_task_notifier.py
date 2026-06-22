import os
import subprocess
from pathlib import Path


SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "feishu-task-notifier"
    / "SKILL.md"
)
SCRIPT_PATH = SKILL_PATH.parent / "scripts" / "feishu-notify"


def frontmatter_description() -> str:
    text = SKILL_PATH.read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("missing description frontmatter")


def test_description_requires_exact_feishu_notification_phrase() -> None:
    description = frontmatter_description()

    assert "飞书通知" in description
    assert "Feishu reminder" not in description
    assert "Feishu push" not in description
    assert "task completes" not in description


def test_notify_script_is_packaged_executable_and_does_not_embed_session() -> None:
    assert SCRIPT_PATH.exists()
    assert os.access(SCRIPT_PATH, os.X_OK)

    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "feishu:oc_" not in script
    assert "CC_NOTIFY_SESSION" in script


def test_notify_script_invokes_cc_connect_with_configured_session(tmp_path: Path) -> None:
    calls_path = tmp_path / "calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_cc_connect = fake_bin / "cc-connect"
    fake_cc_connect.write_text(
        f"""#!/usr/bin/env bash
printf '%s\\n' "$@" > {calls_path}
""",
        encoding="utf-8",
    )
    fake_cc_connect.chmod(0o755)

    env = {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "CC_FEISHU_NOTIFY_CONFIRM": "1",
        "CC_NOTIFY_PROJECT": "notify-project",
        "CC_NOTIFY_SESSION": "feishu:chat:user",
    }
    result = subprocess.run(
        [str(SCRIPT_PATH), "飞书通知测试"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert calls_path.read_text(encoding="utf-8").splitlines() == [
        "send",
        "-p",
        "notify-project",
        "-s",
        "feishu:chat:user",
        "-m",
        "飞书通知测试",
    ]


def test_notify_script_requires_session_even_when_confirmed() -> None:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "CC_FEISHU_NOTIFY_CONFIRM": "1",
    }
    result = subprocess.run(
        [str(SCRIPT_PATH), "飞书通知测试"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 64
    assert "CC_NOTIFY_SESSION" in result.stderr
