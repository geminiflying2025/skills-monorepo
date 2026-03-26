from config import CaptchaConfig, RuntimeConfig, Selectors
from agent_runner import build_solve_endpoint, pick_first_candidate


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
