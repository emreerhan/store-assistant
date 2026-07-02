from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from store_assistant.db import StoreAssistantDB
from store_assistant.llm import HeuristicLLMClient, LLMClient
from store_assistant.models import AssistantResponse, ConversationState, Intent, IntentResult
from store_assistant.normalization import clean_display_name, normalize_store_name
from store_assistant.phone import normalize_us_phone


MAX_OFF_SCOPE_ATTEMPTS = 3


@dataclass
class ConversationController:
    db: StoreAssistantDB
    conversation_id: int
    llm: LLMClient
    lookup_passphrase: str = "open-sesame"
    state: ConversationState = ConversationState.IDLE
    pending_store_name: str | None = None
    pending_lookup_name: str | None = None
    off_scope_count: int = 0

    def handle_user_message(self, message: str) -> AssistantResponse:
        text = message.strip()
        if not text:
            return self._assistant_message("Please send a store save or lookup request.")

        if self.state == ConversationState.ENDED:
            return AssistantResponse(
                "This conversation has ended. Start a new conversation to continue.",
                ended=True,
                end_reason="already_ended",
            )

        self.db.save_message(self.conversation_id, "user", text)

        if self._looks_done(text):
            return self._end_conversation("user_done")

        if self.state == ConversationState.AWAITING_SAVE_NAME:
            return self._handle_save_name(text)
        if self.state == ConversationState.AWAITING_SAVE_PHONE:
            return self._handle_save_phone(text)
        if self.state == ConversationState.AWAITING_LOOKUP_NAME:
            return self._handle_lookup_name(text)
        if self.state == ConversationState.AWAITING_PASSPHRASE:
            return self._handle_passphrase(text)

        intent = self._classify(text)
        if intent.intent == Intent.DONE:
            return self._end_conversation("user_done")
        if intent.intent == Intent.SAVE:
            self.off_scope_count = 0
            return self._start_save(intent)
        if intent.intent == Intent.LOOKUP:
            self.off_scope_count = 0
            return self._start_lookup(intent)
        return self._handle_off_scope()

    @property
    def is_ended(self) -> bool:
        return self.state == ConversationState.ENDED

    def _start_save(self, intent: IntentResult) -> AssistantResponse:
        if not intent.store_name:
            self.state = ConversationState.AWAITING_SAVE_NAME
            return self._assistant_message("What is the store name?")

        self.pending_store_name = clean_display_name(intent.store_name)
        if not intent.phone:
            self.state = ConversationState.AWAITING_SAVE_PHONE
            return self._assistant_message(
                f"What is the phone number for {self.pending_store_name}?"
            )

        return self._save_store(self.pending_store_name, intent.phone)

    def _handle_save_name(self, message: str) -> AssistantResponse:
        name = clean_display_name(message)
        if not name:
            return self._assistant_message("What is the store name?")
        self.pending_store_name = name
        self.state = ConversationState.AWAITING_SAVE_PHONE
        self.off_scope_count = 0
        return self._assistant_message(f"What is the phone number for {name}?")

    def _handle_save_phone(self, message: str) -> AssistantResponse:
        if not self.pending_store_name:
            self.state = ConversationState.AWAITING_SAVE_NAME
            return self._assistant_message("What is the store name?")
        return self._save_store(self.pending_store_name, message)

    def _save_store(self, display_name: str, phone: str) -> AssistantResponse:
        normalized_phone = normalize_us_phone(phone)
        if normalized_phone is None:
            self.state = ConversationState.AWAITING_SAVE_PHONE
            return self._assistant_message(
                "Please provide a valid US phone number, such as (555) 234-5678."
            )

        normalized_name = normalize_store_name(display_name)
        if not normalized_name:
            self.state = ConversationState.AWAITING_SAVE_NAME
            return self._assistant_message("What is the store name?")

        record = self.db.upsert_store(
            normalized_name=normalized_name,
            display_name=clean_display_name(display_name),
            phone=normalized_phone,
        )
        self.pending_store_name = None
        self.state = ConversationState.IDLE
        self.off_scope_count = 0
        return self._assistant_message(
            f"Saved {record.display_name} with phone {record.phone}."
        )

    def _start_lookup(self, intent: IntentResult) -> AssistantResponse:
        if not intent.store_name:
            self.state = ConversationState.AWAITING_LOOKUP_NAME
            return self._assistant_message("Which store should I look up?")
        self.pending_lookup_name = clean_display_name(intent.store_name)
        self.state = ConversationState.AWAITING_PASSPHRASE
        return self._assistant_message("What is the lookup passphrase?")

    def _handle_lookup_name(self, message: str) -> AssistantResponse:
        name = clean_display_name(message)
        if not name:
            return self._assistant_message("Which store should I look up?")
        self.pending_lookup_name = name
        self.state = ConversationState.AWAITING_PASSPHRASE
        self.off_scope_count = 0
        return self._assistant_message("What is the lookup passphrase?")

    def _handle_passphrase(self, message: str) -> AssistantResponse:
        if message.strip() != self.lookup_passphrase:
            return self._assistant_message(
                "I couldn't verify the passphrase, so I won't perform that lookup."
            )

        if not self.pending_lookup_name:
            self.state = ConversationState.AWAITING_LOOKUP_NAME
            return self._assistant_message("Which store should I look up?")

        normalized_name = normalize_store_name(self.pending_lookup_name)
        record = self.db.get_store_by_normalized_name(normalized_name)
        looked_up_name = self.pending_lookup_name
        self.pending_lookup_name = None
        self.state = ConversationState.IDLE
        self.off_scope_count = 0
        if record is None:
            return self._assistant_message(f"I could not find {looked_up_name}.")
        return self._assistant_message(
            f"{record.display_name}'s phone number is {record.phone}."
        )

    def _handle_off_scope(self) -> AssistantResponse:
        self.off_scope_count += 1
        if self.off_scope_count >= MAX_OFF_SCOPE_ATTEMPTS:
            return self._end_conversation("off_scope_limit")
        return self._assistant_message(
            "I can help save or retrieve store phone numbers."
        )

    def _end_conversation(self, reason: str) -> AssistantResponse:
        summary = self._summarize()
        self.db.save_summary(self.conversation_id, summary)
        self.db.end_conversation(self.conversation_id, reason)
        self.state = ConversationState.ENDED
        content = "Got it. I saved a summary of this conversation."
        return self._assistant_message(content, ended=True, end_reason=reason)

    def _assistant_message(
        self, content: str, *, ended: bool = False, end_reason: str | None = None
    ) -> AssistantResponse:
        self.db.save_message(self.conversation_id, "assistant", content)
        return AssistantResponse(content, ended=ended, end_reason=end_reason)

    def _classify(self, message: str) -> IntentResult:
        payload = {"message": message}
        fallback = lambda: HeuristicLLMClient().classify(message)
        return self._trace_llm_call("intent", payload, self.llm.classify, fallback, message)

    def _summarize(self) -> str:
        rows = self.db.list_messages(self.conversation_id)
        messages = [{"role": row["role"], "content": row["content"]} for row in rows]
        payload = {"messages": messages}
        fallback = lambda: HeuristicLLMClient().summarize(messages)
        return self._trace_llm_call("summary", payload, self.llm.summarize, fallback, messages)

    def _trace_llm_call(
        self,
        call_type: str,
        input_payload: dict[str, object],
        fn: Callable,
        fallback: Callable,
        *args: object,
    ):
        started = time.perf_counter()
        try:
            output = fn(*args)
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.db.record_trace(
                conversation_id=self.conversation_id,
                call_type=call_type,
                model=self.llm.model_name,
                input_payload=input_payload,
                output_payload=_serialize_output(output),
                latency_ms=latency_ms,
            )
            return output
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            output = fallback()
            self.db.record_trace(
                conversation_id=self.conversation_id,
                call_type=call_type,
                model=self.llm.model_name,
                input_payload=input_payload,
                output_payload=_serialize_output(output),
                latency_ms=latency_ms,
                error=str(exc),
            )
            return output

    @staticmethod
    def _looks_done(message: str) -> bool:
        return HeuristicLLMClient().classify(message).intent == Intent.DONE


def _serialize_output(output: object) -> dict[str, object]:
    if isinstance(output, IntentResult):
        return output.to_dict()
    return {"output": str(output)}
