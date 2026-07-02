from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from streamlit.testing.v1 import AppTest


def run_app_with_db(tmp_path: Path) -> tuple[AppTest, Path]:
    db_path = tmp_path / "store_assistant.sqlite3"
    os.environ["STORE_ASSISTANT_DB_PATH"] = str(db_path)
    os.environ["STORE_LOOKUP_PASSPHRASE"] = "open-sesame"
    os.environ.pop("OPENAI_API_KEY", None)
    app = AppTest.from_file("streamlit_app.py")
    app.run()
    return app, db_path


def fetch_rows(db_path: Path, query: str) -> list[tuple]:
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(query).fetchall()
    finally:
        connection.close()


def test_streamlit_exact_save_lookup_and_summary(tmp_path: Path) -> None:
    app, db_path = run_app_with_db(tmp_path)

    app.chat_input[0].set_value("Save Aldi with (555) 456-7890").run()
    app.chat_input[0].set_value("Lookup Aldi").run()
    app.chat_input[0].set_value("open-sesame").run()
    app.chat_input[0].set_value("I'm done").run()

    assert fetch_rows(db_path, "select display_name, phone from stores") == [
        ("Aldi", "+15554567890")
    ]
    summaries = fetch_rows(db_path, "select summary from summaries")
    assert len(summaries) == 1
    assert "Saved Aldi (+15554567890)" in summaries[0][0]
    assert "Retrieved Aldi (+15554567890)" in summaries[0][0]
    trace_types = fetch_rows(db_path, "select call_type from llm_traces order by id")
    assert ("intent",) in trace_types
    assert ("summary",) in trace_types


def test_streamlit_convertible_phone_requires_confirmation(tmp_path: Path) -> None:
    app, db_path = run_app_with_db(tmp_path)

    app.chat_input[0].set_value("Save Aldi with 555-456-7890").run()
    assert fetch_rows(db_path, "select display_name, phone from stores") == []

    app.chat_input[0].set_value("yes").run()
    assert fetch_rows(db_path, "select display_name, phone from stores") == [
        ("Aldi", "+15554567890")
    ]


def test_streamlit_invalid_overlong_phone_does_not_save(tmp_path: Path) -> None:
    app, db_path = run_app_with_db(tmp_path)

    app.chat_input[0].set_value("save brooklyn grocers with 3 222 333 5555").run()

    assert fetch_rows(db_path, "select display_name, phone from stores") == []
