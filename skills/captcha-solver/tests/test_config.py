from pathlib import Path

import pytest

from config import load_config


def test_load_config_requires_selector_fields(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("url: https://example.com\nselectors: {}\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(str(cfg))


def test_load_config_success(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        """
url: https://example.com
selectors:
  captcha_image: img#cap
  captcha_input: input#cap
  submit_button: button#submit
runtime:
  max_attempts: 3
""".strip()
        + "\n",
        encoding="utf-8",
    )

    parsed = load_config(str(cfg))
    assert parsed.url == "https://example.com"
    assert parsed.runtime.max_attempts == 3
