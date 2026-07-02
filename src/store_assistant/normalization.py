from __future__ import annotations

import re


_WHITESPACE_RE = re.compile(r"\s+")
_NAME_CHARS_RE = re.compile(r"[^a-z0-9\s]")


def clean_extracted_store_name(name: str | None) -> str | None:
    if not name:
        return None

    candidate = _WHITESPACE_RE.sub(" ", name).strip(" ?!.,-")
    if not candidate:
        return None

    previous = None
    while candidate != previous:
        previous = candidate
        candidate = re.sub(
            r"^(?:please|pls|can you|could you|would you|will you)\b\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(
            r"\s*\b(?:please|pls|for me|thanks|thank you)\b[ ?!.,-]*$",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = _WHITESPACE_RE.sub(" ", candidate).strip(" ?!.,-")
    if candidate.lower() in {"a", "an", "the", "this", "that", "it"}:
        return None
    return candidate or None


def normalize_store_name(name: str) -> str:
    lower = name.strip().lower()
    lower = re.sub(r"'s\b", "", lower)
    cleaned = _NAME_CHARS_RE.sub(" ", lower)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def clean_display_name(name: str) -> str:
    return _WHITESPACE_RE.sub(" ", name.strip())
