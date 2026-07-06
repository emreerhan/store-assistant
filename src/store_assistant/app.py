from __future__ import annotations

from store_assistant.config import Settings, load_settings
from store_assistant.controller import ConversationController
from store_assistant.db import StoreAssistantDB
from store_assistant.llm import HeuristicLLMClient, LLMClient, PydanticAILLMClient


def create_db(settings: Settings | None = None) -> StoreAssistantDB:
    resolved_settings = settings or load_settings()
    db = StoreAssistantDB(resolved_settings.db_path)
    db.init_schema()
    return db


def create_llm_client(settings: Settings | None = None) -> LLMClient:
    resolved_settings = settings or load_settings()
    if resolved_settings.openai_api_key:
        return PydanticAILLMClient(
            resolved_settings.openai_model,
            api_key=resolved_settings.openai_api_key,
        )
    return HeuristicLLMClient()


def create_controller(
    db: StoreAssistantDB,
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> ConversationController:
    resolved_settings = settings or load_settings()
    conversation_id = db.create_conversation()
    return ConversationController(
        db=db,
        conversation_id=conversation_id,
        llm=llm or create_llm_client(resolved_settings),
        lookup_passphrase=resolved_settings.lookup_passphrase,
    )
