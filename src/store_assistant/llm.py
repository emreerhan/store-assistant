from __future__ import annotations

import json
import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from store_assistant.models import Intent, IntentResult
from store_assistant.normalization import clean_extracted_store_name


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
    def __init__(self, model_name: str, api_key: str | None = None):
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIResponsesModel
        from pydantic_ai.providers.openai import OpenAIProvider

        self.model_name = model_name
        model = model_name
        if model_name.startswith("openai:"):
            provider = OpenAIProvider(api_key=api_key)
            model = OpenAIResponsesModel(model_name.removeprefix("openai:"), provider=provider)
        self._intent_agent = Agent(
            model,
            output_type=IntentExtraction,
            instructions=(
                "You classify messages for a narrow store phone assistant. "
                "Allowed intents: save, lookup, done, off_scope, unknown. "
                "Use save when the user wants to add/update a store phone. "
                "Use lookup when the user wants to retrieve a store phone. "
                "Use done when the user says they are done or good. "
                "Use off_scope for anything unrelated to saving or retrieving store phones. "
                "Extract store_name and phone only when present in the user's text. "
                "Do not include request words or politeness such as save, add, store, "
                "phone number, please, or for me in store_name. If the store name is "
                "not clear, leave store_name null so the assistant can ask."
            ),
        )
        self._summary_agent = Agent(
            model,
            output_type=str,
            instructions=(
                "Write a concise summary of the store assistant conversation. "
                "Include the actual store names and phone numbers saved or retrieved, "
                "plus failed invalid-phone, rejected phone confirmation, incorrect "
                "passphrase, not-found, and off-scope attempts when present. "
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
        saved = []
        retrieved = []
        confirmations = 0
        failures = []
        off_scope_count = sum(
            1 for content in user_messages if _looks_off_scope(content.lower())
        )
        assistant_off_scope_count = 0

        for content in assistant_messages:
            saved_match = re.search(r"^Saved (.+) with phone (\+\d+)\.", content)
            if saved_match:
                saved.append(f"{saved_match.group(1)} ({saved_match.group(2)})")
                continue

            retrieved_match = re.search(r"^(.+)'s phone number is (\+\d+)\.", content)
            if retrieved_match:
                retrieved.append(
                    f"{retrieved_match.group(1)} ({retrieved_match.group(2)})"
                )
                continue

            lower = content.lower()
            if "valid us phone" in lower:
                failures.append("invalid phone format")
            elif "did you mean" in lower:
                confirmations += 1
            elif "okay, please provide" in lower:
                failures.append("phone format confirmation rejected")
            elif "couldn't verify" in lower:
                failures.append("incorrect lookup passphrase")
            elif "could not find" in lower:
                failures.append("store not found")
            elif "save or retrieve" in lower:
                assistant_off_scope_count += 1

        off_scope_count = max(off_scope_count, assistant_off_scope_count)

        parts = []
        parts.extend(f"Saved {item}." for item in saved)
        parts.extend(f"Retrieved {item}." for item in retrieved)
        if confirmations:
            parts.append(
                f"Confirmed reformatted phone number(s) {confirmations} time(s)."
            )
        if failures:
            unique_failures = list(dict.fromkeys(failures))
            parts.append("Failed or incomplete attempts: " + ", ".join(unique_failures) + ".")
        if off_scope_count:
            parts.append(f"There were {off_scope_count} off-scope attempt(s).")
        return " ".join(parts) or "No store operations were completed."


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
    trailing_match = re.search(
        r"\b(?:with|at|is|as)\s+([+\d][\d\s().+-]*)$",
        text,
        flags=re.IGNORECASE,
    )
    if trailing_match:
        return trailing_match.group(1).strip()

    match = re.search(
        r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)",
        text,
    )
    if match:
        return match.group(0)
    return None


def _extract_save_name(text: str, phone: str | None) -> str | None:
    candidate = text
    if phone:
        candidate = candidate.replace(phone, " ")
    candidate = re.sub(
        r"\b(?:with|at|as|is)\s+[\d\s().+-]+$",
        " ",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(
        r"\b(save|add|remember|update|store this|store|grocery store|phone|number|with|at|is|as)\b",
        " ",
        candidate,
        flags=re.IGNORECASE,
    )
    return clean_extracted_store_name(candidate)


def _extract_lookup_name(text: str) -> str | None:
    candidate = re.sub(
        r"\b(lookup|look up|retrieve|find|get|what is|what's|the|phone|number|for|store|please)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"'s\b", "", candidate, flags=re.IGNORECASE)
    return clean_extracted_store_name(candidate)
