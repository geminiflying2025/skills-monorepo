from ocr_utils import clean_captcha_text


def test_clean_captcha_text_keeps_alnum_only() -> None:
    assert clean_captcha_text(" A-b c_12! ") == "Abc12"


def test_clean_captcha_text_applies_max_len() -> None:
    assert clean_captcha_text("abc123xyz", max_len=6) == "abc123"
