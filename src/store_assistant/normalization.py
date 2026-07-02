from __future__ import annotations

import re


_WHITESPACE_RE = re.compile(r"\s+")
_NAME_CHARS_RE = re.compile(r"[^a-z0-9\s]")


def normalize_store_name(name: str) -> str:
    lower = name.strip().lower()
    lower = re.sub(r"'s\b", "", lower)
    cleaned = _NAME_CHARS_RE.sub(" ", lower)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def clean_display_name(name: str) -> str:
    return _WHITESPACE_RE.sub(" ", name.strip())
