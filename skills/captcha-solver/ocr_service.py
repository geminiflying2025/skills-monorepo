from __future__ import annotations

import base64

import pytesseract
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ocr_utils import clean_captcha_text, preprocess_image


class SolveRequest(BaseModel):
    image_base64: str


class SolveResponse(BaseModel):
    text: str
    raw_text: str


app = FastAPI(title="captcha-ocr-service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/solve", response_model=SolveResponse)
def solve(body: SolveRequest) -> SolveResponse:
    try:
        image_bytes = base64.b64decode(body.image_base64)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"invalid base64 payload: {exc}") from exc

    try:
        image = preprocess_image(image_bytes)
        raw_text = pytesseract.image_to_string(
            image,
            config="--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        )
        text = clean_captcha_text(raw_text)
        return SolveResponse(text=text, raw_text=raw_text)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"ocr failed: {exc}") from exc
