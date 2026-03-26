from __future__ import annotations

import io
import re

from PIL import Image, ImageFilter, ImageOps


def preprocess_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    threshold = 150
    img = img.point(lambda p: 255 if p > threshold else 0)
    return img


def clean_captcha_text(text: str, max_len: int = 8) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text)
    return cleaned[:max_len]
