from functools import lru_cache
from os import getenv


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = getenv("GEMINI_API_KEY", "")
        self.gemini_model = getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.request_timeout = float(getenv("GEMINI_TIMEOUT_SECONDS", "60"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
