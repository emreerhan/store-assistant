from __future__ import annotations

import json

import streamlit as st

from store_assistant.app import create_controller, create_db
from store_assistant.config import load_settings
from store_assistant.models import ConversationState


def main() -> None:
    st.set_page_config(page_title="Store Assistant", layout="wide")
    settings = load_settings()

    if "db" not in st.session_state:
        st.session_state.db = create_db(settings)
    if "controller" not in st.session_state:
        st.session_state.controller = create_controller(st.session_state.db, settings)
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    controller = st.session_state.controller
    db = st.session_state.db

    chat_tab, stores_tab, summaries_tab, traces_tab = st.tabs(
        ["Chat", "Stores", "Summaries", "Traces"]
    )

    with chat_tab:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        prompt = st.chat_input(
            "Message",
            disabled=controller.state == ConversationState.ENDED,
        )
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            response = controller.handle_user_message(prompt)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response.content}
            )
            st.rerun()

        if controller.state == ConversationState.ENDED:
            st.caption("Conversation ended.")

    with stores_tab:
        stores = db.list_stores()
        if stores:
            st.dataframe(
                [
                    {
                        "Name": store.display_name,
                        "Phone": store.phone,
                        "Updated": store.updated_at,
                    }
                    for store in stores
                ],
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("No stores saved.")

    with summaries_tab:
        summaries = db.list_summaries()
        if summaries:
            for row in summaries:
                st.markdown(f"**Conversation {row['conversation_id']}**")
                st.write(row["summary"])
                st.caption(row["created_at"])
        else:
            st.caption("No summaries saved.")

    with traces_tab:
        traces = db.list_traces()
        if traces:
            for row in traces:
                with st.expander(
                    f"{row['call_type']} · conversation {row['conversation_id']} · {row['created_at']}"
                ):
                    st.write(f"Model: {row['model']}")
                    st.write(f"Latency: {row['latency_ms']} ms")
                    if row["error"]:
                        st.error(row["error"])
                    st.code(_pretty_json(row["input_json"]), language="json")
                    if row["output_json"]:
                        st.code(_pretty_json(row["output_json"]), language="json")
        else:
            st.caption("No traces saved.")


def _pretty_json(payload: str) -> str:
    try:
        return json.dumps(json.loads(payload), indent=2)
    except json.JSONDecodeError:
        return payload
