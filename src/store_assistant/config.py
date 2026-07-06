from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = Path("data/store_assistant.sqlite3")
DEFAULT_LOOKUP_PASSPHRASE = "open-sesame"
DEFAULT_OPENAI_MODEL = "openai:gpt-5.2"
DEFAULT_OPENAI_API_KEY_FILE = Path("openai_api_key.txt")
LEGACY_OPENAI_API_KEY_FILE = Path("openapi_key.txt")


@dataclass(frozen=True)
class Settings:
    db_path: Path | str = DEFAULT_DB_PATH
    lookup_passphrase: str = DEFAULT_LOOKUP_PASSPHRASE
    openai_api_key: str | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL


def load_settings() -> Settings:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    db_path = os.getenv("STORE_ASSISTANT_DB_PATH", str(DEFAULT_DB_PATH))
    api_key_file = os.getenv("OPENAI_API_KEY_FILE")
    return Settings(
        db_path=Path(db_path) if db_path != ":memory:" else ":memory:",
        lookup_passphrase=os.getenv(
            "STORE_LOOKUP_PASSPHRASE", DEFAULT_LOOKUP_PASSPHRASE
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY")
        or _read_openai_api_key_file(api_key_file),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    )


def _read_openai_api_key_file(configured_path: str | None) -> str | None:
    if configured_path:
        return _read_secret_file(configured_path)
    return _read_secret_file(DEFAULT_OPENAI_API_KEY_FILE) or _read_secret_file(
        LEGACY_OPENAI_API_KEY_FILE
    )


def _read_secret_file(path: str | Path) -> str | None:
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return value or None
