from __future__ import annotations

from typing import Any


def _looks_like_note(value: dict[str, Any]) -> bool:
    return any(key in value for key in ("title", "desc", "images", "imageList", "video"))


def _normalize_images(images: Any) -> list[dict[str, Any]]:
    if not isinstance(images, list):
        return []

    normalized: list[dict[str, Any]] = []
    for image in images:
        if isinstance(image, str):
            url = image.strip()
            if url:
                normalized.append({"urlDefault": url, "urlPre": url})
            continue
        if not isinstance(image, dict):
            continue

        copied = dict(image)
        url = (
            copied.get("urlDefault")
            or copied.get("urlPre")
            or copied.get("url")
            or copied.get("src")
            or copied.get("href")
        )
        if url and "urlDefault" not in copied:
            copied["urlDefault"] = url
        if url and "urlPre" not in copied:
            copied["urlPre"] = url
        if copied.get("urlDefault") or copied.get("urlPre"):
            normalized.append(copied)
    return normalized


def _normalize_domestic_note(payload: dict[str, Any], feed_id: str = "", xsec_token: str = "") -> dict[str, Any]:
    image_list = payload.get("imageList")
    if not image_list:
        image_list = _normalize_images(payload.get("images"))

    interact_info = payload.get("interactInfo")
    if not isinstance(interact_info, dict):
        interact_info = {
            "likedCount": payload.get("likedCount") or payload.get("likeCount"),
            "commentCount": payload.get("commentCount"),
            "collectedCount": payload.get("collectedCount") or payload.get("favoriteCount"),
            "shareCount": payload.get("shareCount"),
        }

    note = dict(payload)
    note["noteId"] = payload.get("noteId") or payload.get("id") or feed_id
    note["xsecToken"] = payload.get("xsecToken") or payload.get("xsec_token") or xsec_token
    note["title"] = payload.get("title") or ""
    note["desc"] = payload.get("desc") or payload.get("content") or ""
    note["user"] = payload.get("user") if isinstance(payload.get("user"), dict) else {}
    note["interactInfo"] = {key: value for key, value in interact_info.items() if value not in (None, "")}
    note["imageList"] = image_list if isinstance(image_list, list) else []
    note["time"] = payload.get("time") or payload.get("createTime")
    note["type"] = payload.get("type") or ("video" if payload.get("video") else "normal")
    return note


def extract_note_from_payload(payload: dict[str, Any], feed_id: str = "", xsec_token: str = "") -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    data = payload.get("data")
    if isinstance(data, dict):
        note = data.get("note")
        if isinstance(note, dict) and note:
            return note
        if _looks_like_note(data):
            return _normalize_domestic_note(data, feed_id=feed_id, xsec_token=xsec_token)

    if _looks_like_note(payload):
        return _normalize_domestic_note(payload, feed_id=feed_id, xsec_token=xsec_token)

    return {}
