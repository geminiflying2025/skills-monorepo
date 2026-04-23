from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path


__path__ = extend_path(__path__, __name__)
APP_PACKAGE = Path(__file__).resolve().parents[2] / "apps/content-hub/content_hub"
if str(APP_PACKAGE) not in __path__:
    __path__.append(str(APP_PACKAGE))
