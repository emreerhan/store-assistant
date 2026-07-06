from __future__ import annotations

import os

import pytest

from store_assistant.app import create_controller, create_db
from store_assistant.config import Settings, load_settings
from store_assistant.models import ConversationState


pytestmark = pytest.mark.live_openai


def live_settings() -> Settings:
    settings = load_settings()
    if os.getenv("STORE_ASSISTANT_RUN_LIVE_OPENAI") != "1":
        pytest.skip("set STORE_ASSISTANT_RUN_LIVE_OPENAI=1 to run live OpenAI tests")
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY or openapi_key.txt is required")
    return Settings(
        db_path=":memory:",
        lookup_passphrase="open-sesame",
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
    )


def test_live_openai_save_lookup_and_summary_flow() -> None:
    settings = live_settings()
    db = create_db(settings)
    controller = create_controller(db, settings)

    response = controller.handle_user_message(
        "Please save a grocery store named Aldi with phone (555) 456-7890."
    )
    assert "Saved" in response.content
    assert "+15554567890" in response.content

    response = controller.handle_user_message("Please look up Aldi's phone number.")
    assert "passphrase" in response.content.lower()
    assert "+15554567890" not in response.content

    response = controller.handle_user_message("wrong")
    assert "won't perform" in response.content
    assert "+15554567890" not in response.content

    response = controller.handle_user_message("open-sesame")
    assert "phone number is +15554567890" in response.content
    assert controller.state == ConversationState.IDLE

    response = controller.handle_user_message("I'm done")
    assert response.ended is True

    summaries = db.list_summaries()
    assert len(summaries) == 1
    assert summaries[0]["summary"].strip()

    traces = db.list_traces()
    assert {trace["call_type"] for trace in traces} >= {"intent", "summary"}
    assert all(trace["model"] == settings.openai_model for trace in traces)
    assert all(trace["error"] is None for trace in traces)
