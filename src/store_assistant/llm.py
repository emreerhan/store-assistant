from __future__ import annotations

import json
import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from store_assistant.models import Intent, IntentResult


class LLMClient(Protocol):
    model_name: str

    def classify(self, message: str) -> IntentResult:
        ...

    def summarize(self, messages: list[dict[str, str]]) -> str:
        ...


class IntentExtraction(BaseModel):
    intent: Literal["save", "lookup", "done", "off_scope", "unknown"] = Field(
        description="The user's intent within the store assistant scope."
    )
    store_name: str | None = Field(
        default=None, description="Store name if explicitly present."
    )
    phone: str | None = Field(
        default=None, description="Phone number if explicitly present."
    )


class PydanticAILLMClient:
    def __init__(self, model_name: str):
        from pydantic_ai import Agent

        self.model_name = model_name
        self._intent_agent = Agent(
            model_name,
            output_type=IntentExtraction,
            instructions=(
                "You classify messages for a narrow store phone assistant. "
                "Allowed intents: save, lookup, done, off_scope, unknown. "
                "Use save when the user wants to add/update a store phone. "
                "Use lookup when the user wants to retrieve a store phone. "
                "Use done when the user says they are done or good. "
                "Use off_scope for anything unrelated to saving or retrieving store phones. "
                "Extract store_name and phone only when present in the user's text."
            ),
        )
        self._summary_agent = Agent(
            model_name,
            output_type=str,
            instructions=(
                "Write a concise summary of the store assistant conversation. "
                "Include successful operations, failed attempts, and off-scope attempts. "
                "Keep it to 2-4 short sentences."
            ),
        )

    def classify(self, message: str) -> IntentResult:
        result = self._intent_agent.run_sync(message)
        output = result.output
        return IntentResult(
            intent=Intent(output.intent),
            store_name=output.store_name,
            phone=output.phone,
        )

    def summarize(self, messages: list[dict[str, str]]) -> str:
        prompt = json.dumps(messages, indent=2)
        result = self._summary_agent.run_sync(prompt)
        return str(result.output).strip()


class HeuristicLLMClient:
    model_name = "heuristic-local"

    def classify(self, message: str) -> IntentResult:
        text = message.strip()
        lower = text.lower()
        phone = _extract_phone(text)

        if _looks_done(lower):
            return IntentResult(Intent.DONE)

        if _looks_off_scope(lower):
            return IntentResult(Intent.OFF_SCOPE)

        if _looks_save(lower):
            return IntentResult(
                Intent.SAVE,
                store_name=_extract_save_name(text, phone),
                phone=phone,
            )

        if _looks_lookup(lower):
            return IntentResult(
                Intent.LOOKUP,
                store_name=_extract_lookup_name(text),
            )

        return IntentResult(Intent.UNKNOWN)

    def summarize(self, messages: list[dict[str, str]]) -> str:
        user_messages = [m["content"] for m in messages if m["role"] == "user"]
        assistant_messages = [m["content"] for m in messages if m["role"] == "assistant"]
        successes = sum(
            1
            for content in assistant_messages
            if "saved" in content.lower() or "phone number is" in content.lower()
        )
        failures = sum(
            1
            for content in assistant_messages
            if "valid us phone" in content.lower()
            or "couldn't verify" in content.lower()
            or "not found" in content.lower()
        )
        off_scope = sum(
            1 for content in assistant_messages if "save or retrieve" in content.lower()
        )
        return (
            f"The conversation had {len(user_messages)} user message(s), "
            f"{successes} successful operation(s), {failures} failed attempt(s), "
            f"and {off_scope} off-scope attempt(s)."
        )


def _looks_done(lower: str) -> bool:
    done_phrases = {
        "i'm done",
        "im done",
        "i am done",
        "i'm good",
        "im good",
        "i am good",
        "all done",
        "that's all",
        "thats all",
        "no more",
    }
    return lower in done_phrases or any(phrase in lower for phrase in done_phrases)


def _looks_save(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "save",
            "add",
            "store this",
            "remember",
            "update",
        )
    )


def _looks_lookup(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "lookup",
            "look up",
            "retrieve",
            "find",
            "get",
            "what is",
            "what's",
            "phone for",
            "phone number for",
        )
    )


def _looks_off_scope(lower: str) -> bool:
    return any(
        token in lower
        for token in (
            "weather",
            "recipe",
            "joke",
            "movie",
            "sports",
            "news",
            "homework",
            "poem",
        )
    )


def _extract_phone(text: str) -> str | None:
    match = re.search(
        r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}",
        text,
    )
    return match.group(0) if match else None


def _extract_save_name(text: str, phone: str | None) -> str | None:
    candidate = text
    if phone:
        candidate = candidate.replace(phone, " ")
    candidate = re.sub(
        r"\b(save|add|remember|update|store this|store|grocery store|phone|number|with|at|is|as)\b",
        " ",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,.-")
    return candidate or None


def _extract_lookup_name(text: str) -> str | None:
    candidate = re.sub(
        r"\b(lookup|look up|retrieve|find|get|what is|what's|the|phone|number|for|store|please)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"'s\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ?.,")
    return candidate or None
