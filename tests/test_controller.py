from __future__ import annotations

from store_assistant.controller import ConversationController
from store_assistant.db import StoreAssistantDB
from store_assistant.llm import HeuristicLLMClient
from store_assistant.models import ConversationState


def make_controller(passphrase: str = "open-sesame") -> tuple[StoreAssistantDB, ConversationController]:
    db = StoreAssistantDB(":memory:")
    db.init_schema()
    controller = ConversationController(
        db=db,
        conversation_id=db.create_conversation(),
        llm=HeuristicLLMClient(),
        lookup_passphrase=passphrase,
    )
    return db, controller


def test_invalid_phone_reprompts_and_does_not_save() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Trader Joe's")
    assert "phone number" in response.content

    response = controller.handle_user_message("123")
    assert "valid US phone" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE
    assert db.list_stores() == []

    response = controller.handle_user_message("(555) 234-5678")
    assert "Saved Trader Joe's" in response.content
    assert controller.state == ConversationState.IDLE
    stores = db.list_stores()
    assert len(stores) == 1
    assert stores[0].phone == "+15552345678"


def test_lookup_is_gated_by_passphrase() -> None:
    db, controller = make_controller(passphrase="secret")
    controller.handle_user_message("Save Trader Joe's with (555) 234-5678")

    response = controller.handle_user_message("What is Trader Joe's phone?")
    assert "passphrase" in response.content

    response = controller.handle_user_message("wrong")
    assert "won't perform" in response.content
    assert "+15552345678" not in response.content

    response = controller.handle_user_message("secret")
    assert "phone number is +15552345678" in response.content
    assert controller.state == ConversationState.IDLE


def test_repeated_mixed_operations_in_one_conversation() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Trader Joe's with (555) 234-5678")
    controller.handle_user_message("Lookup Trader Joe")
    controller.handle_user_message("open-sesame")
    controller.handle_user_message("Save Whole Foods with 555-345-6789")

    stores = db.list_stores()
    assert [store.display_name for store in stores] == ["Trader Joe's", "Whole Foods"]
    assert controller.state == ConversationState.IDLE


def test_off_scope_termination_saves_summary() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Tell me a joke")
    controller.handle_user_message("What is the weather?")
    response = controller.handle_user_message("Recommend a movie")

    assert response.ended is True
    assert response.end_reason == "off_scope_limit"
    assert controller.state == ConversationState.ENDED
    summaries = db.list_summaries()
    assert len(summaries) == 1
    assert "off-scope" in summaries[0]["summary"]


def test_messages_and_llm_traces_are_persisted() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Aldi with 555-456-7890")
    controller.handle_user_message("I'm done")

    messages = db.list_messages(controller.conversation_id)
    traces = db.list_traces()

    assert [message["role"] for message in messages][:2] == ["user", "assistant"]
    assert {trace["call_type"] for trace in traces} >= {"intent", "summary"}
