from __future__ import annotations

import re
from dataclasses import dataclass


_DIGIT_RE = re.compile(r"\D")
_EXACT_US_PHONE_RE = re.compile(r"^\(\d{3}\) \d{3}-\d{4}$")
_EXACT_US_PHONE_WITH_COUNTRY_RE = re.compile(r"^\+1 \(\d{3}\) \d{3}-\d{4}$")


@dataclass(frozen=True)
class PhoneInterpretation:
    normalized: str
    display: str
    exact_format: bool


def normalize_us_phone(phone: str) -> str | None:
    interpretation = interpret_us_phone(phone)
    return interpretation.normalized if interpretation else None


def interpret_us_phone(phone: str) -> PhoneInterpretation | None:
    digits = _DIGIT_RE.sub("", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    exact_format = is_exact_us_phone_format(phone)
    return PhoneInterpretation(
        normalized=f"+1{digits}",
        display=format_us_phone_with_country(digits),
        exact_format=exact_format,
    )


def is_valid_us_phone(phone: str) -> bool:
    return normalize_us_phone(phone) is not None


def is_exact_us_phone_format(phone: str) -> bool:
    value = phone.strip()
    return bool(
        _EXACT_US_PHONE_RE.fullmatch(value)
        or _EXACT_US_PHONE_WITH_COUNTRY_RE.fullmatch(value)
    )


def format_us_phone(digits: str) -> str:
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def format_us_phone_with_country(digits: str) -> str:
    return f"+1 {format_us_phone(digits)}"
