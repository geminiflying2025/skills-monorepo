from config import CaptchaConfig, RuntimeConfig, Selectors
from agent_runner import (
    DEFAULT_KANYANBAO_STORAGE_STATE,
    extract_redirect_target_url,
    _is_submission_success,
    build_solve_endpoint,
    pick_first_candidate,
    resolve_storage_state_path,
)


def test_build_solve_endpoint_uses_config_base_url() -> None:
    cfg = CaptchaConfig(
        url="https://example.com",
        selectors=Selectors(
            captcha_image="img#cap",
            captcha_input="input#cap",
            submit_button="button#submit",
        ),
        runtime=RuntimeConfig(ocr_base_url="http://127.0.0.1:8765"),
    )
    assert build_solve_endpoint(cfg) == "http://127.0.0.1:8765/solve"


def test_pick_first_candidate_returns_first_match() -> None:
    candidates = ["a", "b", "c"]
    matched = pick_first_candidate(candidates, lambda x: x in {"b", "c"})
    assert matched == "b"


def test_resolve_storage_state_path_prefers_explicit_value() -> None:
    assert (
        resolve_storage_state_path("https://www.kanyanbao.com/foo", "/tmp/custom.json")
        == "/tmp/custom.json"
    )


def test_resolve_storage_state_path_uses_kanyanbao_default() -> None:
    assert (
        resolve_storage_state_path("https://www.kanyanbao.com/foo", None)
        == DEFAULT_KANYANBAO_STORAGE_STATE
    )


def test_submission_success_when_download_started_even_if_page_unchanged() -> None:
    assert _is_submission_success(
        download_started=True,
        target_reached=False,
        explicit_error=False,
        text_error=False,
        still_on_challenge=True,
    )


def test_submission_success_when_redirect_target_reached() -> None:
    assert _is_submission_success(
        download_started=False,
        target_reached=True,
        explicit_error=False,
        text_error=False,
        still_on_challenge=True,
    )


def test_extract_redirect_target_url_returns_absolute_url() -> None:
    url = (
        "https://www.kanyanbao.com/new/view/report/download_check.jsp"
        "?redirect_url=%2Fimageserver%2Freport%2Fdownload.htm%3Fid%3D42983258"
    )
    assert (
        extract_redirect_target_url(url)
        == "https://www.kanyanbao.com/imageserver/report/download.htm?id=42983258"
    )
