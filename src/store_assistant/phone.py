from __future__ import annotations

import re


_DIGIT_RE = re.compile(r"\D")


def normalize_us_phone(phone: str) -> str | None:
    digits = _DIGIT_RE.sub("", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"+1{digits}"


def is_valid_us_phone(phone: str) -> bool:
    return normalize_us_phone(phone) is not None
