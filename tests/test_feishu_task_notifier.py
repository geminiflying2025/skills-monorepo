from pathlib import Path


SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "feishu-task-notifier"
    / "SKILL.md"
)


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
