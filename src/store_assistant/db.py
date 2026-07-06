from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from store_assistant.models import StoreRecord


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class StoreAssistantDB:
    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'active',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                end_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS llm_traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                call_type TEXT NOT NULL,
                model TEXT NOT NULL,
                input_json TEXT NOT NULL,
                output_json TEXT,
                latency_ms INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )
        self.conn.commit()

    def create_conversation(self) -> int:
        cursor = self.conn.execute(
            "INSERT INTO conversations (status, started_at) VALUES (?, ?)",
            ("active", utc_now()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def end_conversation(self, conversation_id: int, reason: str) -> None:
        self.conn.execute(
            """
            UPDATE conversations
            SET status = 'ended', ended_at = ?, end_reason = ?
            WHERE id = ?
            """,
            (utc_now(), reason, conversation_id),
        )
        self.conn.commit()

    def save_message(self, conversation_id: int, role: str, content: str) -> None:
        self.conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, utc_now()),
        )
        self.conn.commit()

    def list_messages(self, conversation_id: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            )
        )

    def list_all_messages(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages
                ORDER BY id DESC
                """
            )
        )

    def save_summary(self, conversation_id: int, summary: str) -> None:
        self.conn.execute(
            """
            INSERT INTO summaries (conversation_id, summary, created_at)
            VALUES (?, ?, ?)
            """,
            (conversation_id, summary, utc_now()),
        )
        self.conn.commit()

    def list_summaries(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT s.id, s.conversation_id, s.summary, s.created_at
                FROM summaries s
                ORDER BY s.id DESC
                """
            )
        )

    def upsert_store(
        self, *, normalized_name: str, display_name: str, phone: str
    ) -> StoreRecord:
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO stores (normalized_name, display_name, phone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(normalized_name) DO UPDATE SET
                display_name = excluded.display_name,
                phone = excluded.phone,
                updated_at = excluded.updated_at
            """,
            (normalized_name, display_name, phone, now, now),
        )
        self.conn.commit()
        record = self.get_store_by_normalized_name(normalized_name)
        if record is None:
            raise RuntimeError("store upsert succeeded but record could not be read")
        return record

    def get_store_by_normalized_name(self, normalized_name: str) -> StoreRecord | None:
        row = self.conn.execute(
            """
            SELECT id, normalized_name, display_name, phone, created_at, updated_at
            FROM stores
            WHERE normalized_name = ?
            """,
            (normalized_name,),
        ).fetchone()
        return _row_to_store(row) if row else None

    def list_stores(self) -> list[StoreRecord]:
        rows = self.conn.execute(
            """
            SELECT id, normalized_name, display_name, phone, created_at, updated_at
            FROM stores
            ORDER BY display_name COLLATE NOCASE ASC
            """
        )
        return [_row_to_store(row) for row in rows]

    def record_trace(
        self,
        *,
        conversation_id: int,
        call_type: str,
        model: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any] | None,
        latency_ms: int,
        error: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO llm_traces (
                conversation_id, call_type, model, input_json, output_json,
                latency_ms, error, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                call_type,
                model,
                json.dumps(input_payload, sort_keys=True),
                json.dumps(output_payload, sort_keys=True) if output_payload else None,
                latency_ms,
                error,
                utc_now(),
            ),
        )
        self.conn.commit()

    def list_traces(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, conversation_id, call_type, model, input_json, output_json,
                       latency_ms, error, created_at
                FROM llm_traces
                ORDER BY id DESC
                """
            )
        )


def _row_to_store(row: sqlite3.Row) -> StoreRecord:
    return StoreRecord(
        id=int(row["id"]),
        normalized_name=str(row["normalized_name"]),
        display_name=str(row["display_name"]),
        phone=str(row["phone"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
