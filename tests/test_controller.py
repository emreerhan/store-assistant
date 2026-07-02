from __future__ import annotations

from store_assistant.controller import ConversationController
from store_assistant.db import StoreAssistantDB
from store_assistant.llm import HeuristicLLMClient
from store_assistant.models import ConversationState, Intent, IntentResult


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


def test_save_supports_store_name_and_exact_phone_in_same_message() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message(
        "Save Trader Joe's with +1 (555) 234-5678"
    )

    assert "Saved Trader Joe's" in response.content
    assert db.list_stores()[0].phone == "+15552345678"


def test_exact_valid_phone_without_country_code_saves_immediately() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Aldi with (555) 456-7890")

    assert "Saved Aldi" in response.content
    assert controller.state == ConversationState.IDLE
    assert db.list_stores()[0].phone == "+15554567890"


def test_partial_phone_in_save_request_is_not_added_to_store_name() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("save trader joe's supermarket with 123")
    assert "valid US phone" in response.content

    response = controller.handle_user_message("(667) 123-4321")
    assert "Saved trader joe's supermarket" in response.content

    stores = db.list_stores()
    assert len(stores) == 1
    assert stores[0].display_name == "trader joe's supermarket"
    assert stores[0].phone == "+16671234321"


def test_us_phone_validation_is_format_level() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Corner Market with 1234321235")
    assert response.content == (
        "Did you mean +1 (123) 432-1235? Reply yes to save it or no to enter it again."
    )
    assert db.list_stores() == []

    response = controller.handle_user_message("yes")
    assert "Saved Corner Market" in response.content
    assert db.list_stores()[0].phone == "+11234321235"


def test_convertible_dashed_phone_requires_confirmation() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Aldi with 555-456-7890")

    assert "Did you mean +1 (555) 456-7890" in response.content
    assert controller.state == ConversationState.AWAITING_PHONE_CONFIRMATION
    assert db.list_stores() == []

    response = controller.handle_user_message("yes")
    assert "Saved Aldi" in response.content
    assert db.list_stores()[0].phone == "+15554567890"


def test_overlong_phone_in_save_request_reprompts_and_does_not_save() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("save whole foods c with 433213213211")

    assert "valid US phone" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE
    assert db.list_stores() == []

    response = controller.handle_user_message("(433) 213-2132")
    assert "Saved whole foods c" in response.content
    assert db.list_stores()[0].phone == "+14332132132"


def test_spaced_overlong_phone_in_save_request_reprompts_and_does_not_save() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("save brooklyn grocers with 3 222 333 5555")

    assert "valid US phone" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE
    assert db.list_stores() == []


def test_controller_rejects_overlong_phone_even_if_llm_extracts_valid_substring() -> None:
    class BadExtractionLLM:
        model_name = "bad-extraction"

        def classify(self, message: str) -> IntentResult:
            return IntentResult(
                Intent.SAVE,
                store_name="brooklyn grocers",
                phone="222 333 5555",
            )

        def summarize(self, messages: list[dict[str, str]]) -> str:
            return "summary"

    db = StoreAssistantDB(":memory:")
    db.init_schema()
    controller = ConversationController(
        db=db,
        conversation_id=db.create_conversation(),
        llm=BadExtractionLLM(),
    )

    response = controller.handle_user_message(
        "save brooklyn grocers with 3 222 333 5555"
    )

    assert "valid US phone" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE
    assert db.list_stores() == []


def test_phone_confirmation_can_be_rejected_and_reentered() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Corner Market with 1234321235")
    assert "Did you mean +1 (123) 432-1235" in response.content

    response = controller.handle_user_message("no")
    assert "format (555) 234-5678" in response.content

    response = controller.handle_user_message("(222) 333-4444")
    assert "Saved Corner Market" in response.content
    assert db.list_stores()[0].phone == "+12223334444"


def test_confirmation_unclear_response_reprompts_without_saving() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Corner Market with 1234321235")
    response = controller.handle_user_message("maybe")

    assert "Please reply yes" in response.content
    assert controller.state == ConversationState.AWAITING_PHONE_CONFIRMATION
    assert db.list_stores() == []


def test_save_missing_name_then_exact_phone() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("save")
    assert "store name" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_NAME

    response = controller.handle_user_message("Aldi")
    assert "phone number for Aldi" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE

    response = controller.handle_user_message("(555) 456-7890")
    assert "Saved Aldi" in response.content
    assert db.list_stores()[0].phone == "+15554567890"


def test_save_missing_phone_then_exact_phone() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("save Trader Joe's")
    assert "phone number for Trader Joe's" in response.content
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE

    response = controller.handle_user_message("(555) 234-5678")
    assert "Saved Trader Joe's" in response.content
    assert db.list_stores()[0].phone == "+15552345678"


def test_save_name_extraction_strips_polite_suffix_before_phone_prompt() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("add brooklyn grocers please")

    assert response.content == "What is the phone number for brooklyn grocers?"
    assert controller.state == ConversationState.AWAITING_SAVE_PHONE
    assert controller.pending_store_name == "brooklyn grocers"

    response = controller.handle_user_message("(555) 222-3333")
    assert "Saved brooklyn grocers" in response.content
    assert db.list_stores()[0].display_name == "brooklyn grocers"


def test_controller_cleans_polite_store_name_from_llm_output() -> None:
    class PoliteNameLLM:
        model_name = "polite-name"

        def classify(self, message: str) -> IntentResult:
            return IntentResult(Intent.SAVE, store_name="brooklyn grocers please")

        def summarize(self, messages: list[dict[str, str]]) -> str:
            return "summary"

    db = StoreAssistantDB(":memory:")
    db.init_schema()
    controller = ConversationController(
        db=db,
        conversation_id=db.create_conversation(),
        llm=PoliteNameLLM(),
    )

    response = controller.handle_user_message("add brooklyn grocers please")

    assert response.content == "What is the phone number for brooklyn grocers?"
    assert controller.pending_store_name == "brooklyn grocers"


def test_unclear_save_name_prompts_for_store_name() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("add please")

    assert response.content == "What is the store name?"
    assert controller.state == ConversationState.AWAITING_SAVE_NAME
    assert controller.pending_store_name is None


def test_save_request_with_only_filler_name_prompts_for_store_name() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("add the store please")

    assert response.content == "What is the store name?"
    assert controller.state == ConversationState.AWAITING_SAVE_NAME
    assert controller.pending_store_name is None


def test_controller_clarifies_unclear_llm_store_name_output() -> None:
    class UnclearNameLLM:
        model_name = "unclear-name"

        def classify(self, message: str) -> IntentResult:
            return IntentResult(Intent.SAVE, store_name="please")

        def summarize(self, messages: list[dict[str, str]]) -> str:
            return "summary"

    db = StoreAssistantDB(":memory:")
    db.init_schema()
    controller = ConversationController(
        db=db,
        conversation_id=db.create_conversation(),
        llm=UnclearNameLLM(),
    )

    response = controller.handle_user_message("add please")

    assert response.content == "What is the store name?"
    assert controller.state == ConversationState.AWAITING_SAVE_NAME
    assert controller.pending_store_name is None


def test_awaiting_phone_spaced_number_requires_confirmation_before_save() -> None:
    db, controller = make_controller()

    controller.handle_user_message("save hello")
    controller.handle_user_message("123")
    response = controller.handle_user_message("123 123 1234")

    assert response.content == (
        "Did you mean +1 (123) 123-1234? Reply yes to save it or no to enter it again."
    )
    assert controller.state == ConversationState.AWAITING_PHONE_CONFIRMATION
    assert db.list_stores() == []

    response = controller.handle_user_message("yes")
    assert "Saved hello" in response.content
    assert db.list_stores()[0].phone == "+11231231234"


def test_upsert_existing_store_updates_single_row() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Aldi with (555) 111-2222")
    controller.handle_user_message("Save Aldi with (555) 333-4444")

    stores = db.list_stores()
    assert len(stores) == 1
    assert stores[0].display_name == "Aldi"
    assert stores[0].phone == "+15553334444"


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
    response = controller.handle_user_message("Save Whole Foods with 555-345-6789")
    assert "Did you mean +1 (555) 345-6789" in response.content
    controller.handle_user_message("yes")

    stores = db.list_stores()
    assert [store.display_name for store in stores] == ["Trader Joe's", "Whole Foods"]
    assert controller.state == ConversationState.IDLE


def test_multiple_operations_include_lookup_miss() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("Save Aldi with (555) 456-7890")
    assert "Saved Aldi" in response.content

    response = controller.handle_user_message("Lookup Missing Market")
    assert "passphrase" in response.content

    response = controller.handle_user_message("open-sesame")
    assert "could not find Missing Market" in response.content
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

    controller.handle_user_message("Save Aldi with (555) 456-7890")
    controller.handle_user_message("I'm done")

    messages = db.list_messages(controller.conversation_id)
    traces = db.list_traces()

    assert [message["role"] for message in messages][:2] == ["user", "assistant"]
    assert {trace["call_type"] for trace in traces} >= {"intent", "summary"}


def test_done_ends_conversation_and_blocks_further_mutation() -> None:
    db, controller = make_controller()

    response = controller.handle_user_message("I'm done")
    assert response.ended is True

    response = controller.handle_user_message("Save Aldi with (555) 456-7890")
    assert response.ended is True
    assert db.list_stores() == []


def test_in_scope_message_resets_off_scope_counter() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Tell me a joke")
    controller.handle_user_message("Save Aldi with (555) 456-7890")
    controller.handle_user_message("What is the weather?")
    response = controller.handle_user_message("Recommend a movie")

    assert response.ended is False
    assert controller.state == ConversationState.IDLE

    response = controller.handle_user_message("Write a poem")
    assert response.ended is True
    assert response.end_reason == "off_scope_limit"


def test_summary_includes_actual_session_activity() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Aldi with (555) 456-7890")
    controller.handle_user_message("Lookup Aldi")
    controller.handle_user_message("wrong")
    controller.handle_user_message("open-sesame")
    controller.handle_user_message("I'm done")

    summary = db.list_summaries()[0]["summary"]
    assert "Saved Aldi (+15554567890)" in summary
    assert "Retrieved Aldi (+15554567890)" in summary
    assert "incorrect lookup passphrase" in summary


def test_summary_separates_successful_phone_confirmation_from_failures() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Aldi with 555-456-7890")
    controller.handle_user_message("yes")
    controller.handle_user_message("I'm done")

    summary = db.list_summaries()[0]["summary"]
    assert "Saved Aldi (+15554567890)" in summary
    assert "Confirmed reformatted phone number(s) 1 time(s)" in summary
    assert "Failed or incomplete attempts" not in summary


def test_summary_captures_mixed_successes_failures_and_off_scope_attempts() -> None:
    db, controller = make_controller()

    controller.handle_user_message("Save Aldi with 555-456-7890")
    controller.handle_user_message("no")
    controller.handle_user_message("(555) 456-7890")
    controller.handle_user_message("Save Whole Foods with (555) 345-6789")
    controller.handle_user_message("Lookup Whole Foods")
    controller.handle_user_message("wrong")
    controller.handle_user_message("open-sesame")
    controller.handle_user_message("Tell me a joke")
    controller.handle_user_message("I'm done")

    summary = db.list_summaries()[0]["summary"]
    assert "Saved Aldi (+15554567890)" in summary
    assert "Saved Whole Foods (+15553456789)" in summary
    assert "Retrieved Whole Foods (+15553456789)" in summary
    assert "phone format confirmation rejected" in summary
    assert "incorrect lookup passphrase" in summary
    assert "off-scope" in summary
