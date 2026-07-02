from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Intent(StrEnum):
    SAVE = "save"
    LOOKUP = "lookup"
    DONE = "done"
    OFF_SCOPE = "off_scope"
    UNKNOWN = "unknown"


class ConversationState(StrEnum):
    IDLE = "idle"
    AWAITING_SAVE_NAME = "awaiting_save_name"
    AWAITING_SAVE_PHONE = "awaiting_save_phone"
    AWAITING_PHONE_CONFIRMATION = "awaiting_phone_confirmation"
    AWAITING_LOOKUP_NAME = "awaiting_lookup_name"
    AWAITING_PASSPHRASE = "awaiting_passphrase"
    ENDED = "ended"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    store_name: str | None = None
    phone: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "store_name": self.store_name,
            "phone": self.phone,
        }


@dataclass(frozen=True)
class StoreRecord:
    id: int
    normalized_name: str
    display_name: str
    phone: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AssistantResponse:
    content: str
    ended: bool = False
    end_reason: str | None = None
