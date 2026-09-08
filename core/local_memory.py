import os
import sqlite3
import threading
from pathlib import Path
from typing import List
from .app_config import MEMORY_DB_PATH

DEFAULT_MEMORY_DB = MEMORY_DB_PATH

class LocalMemoryStore:
    """SQLite-backed durable facts and bounded summaries, not full chat transcripts."""

    def __init__(self, db_path: str = str(DEFAULT_MEMORY_DB)):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _ensure_schema(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    conversation_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_memory(self, role: str, content: str) -> None:
        if not role or not content or not str(content).strip():
            return

        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT INTO memories(role, content) VALUES (?, ?)",
                (role.strip(), str(content).strip()),
            )
            conn.commit()

    def get_recent_history(self, limit: int = 8) -> List[dict]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT role, content FROM memories ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()

        history = []
        for row in reversed(rows):
            history.append({"role": row["role"], "content": row["content"]})
        return history

    def get_memory_summary(self, limit: int = 4, max_chars: int = 900) -> str:
        history = self.get_recent_history(limit=limit)
        lines = []
        facts = self.get_facts(limit=12)
        if facts:
            lines.append("Durable user facts:")
            lines.extend(f"- {fact['content']}" for fact in facts)

        summaries = self.get_conversation_summaries(limit=4)
        if summaries:
            lines.append("Conversation summaries:")
            lines.extend(f"- {summary}" for summary in summaries)
        elif not history:
            return "\n".join(lines) if lines else "No local memory saved yet."

        if not summaries:
            lines.append("Recent conversation:")
            for item in history:
                role = item.get("role", "user")
                content = item.get("content", "")
                lines.append(f"{role.title()}: {content}")
        return "\n".join(lines)[:max_chars]

    def save_conversation_summary(self, conversation_id: str, messages: List[dict], max_chars: int = 600) -> None:
        if not conversation_id:
            return
        recent = []
        for message in messages[-6:]:
            role = str(message.get("role", "")).strip().title()
            content = str(message.get("content", "")).strip()
            if role and content:
                recent.append(f"{role}: {content}")
        summary = "\n".join(recent)[-max_chars:]
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO conversation_summaries(conversation_id, summary, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    summary = excluded.summary,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (conversation_id, summary),
            )
            conn.commit()

    def get_conversation_summaries(self, limit: int = 4) -> List[str]:
        with self._lock:
            rows = self._connect().execute(
                "SELECT summary FROM conversation_summaries WHERE summary <> '' ORDER BY updated_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [row["summary"] for row in rows]

    def add_fact(self, content: str, category: str = "general") -> None:
        value = str(content or "").strip()
        if not value:
            return
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR IGNORE INTO facts(content, category) VALUES (?, ?)",
                (value, str(category or "general").strip()),
            )
            conn.commit()

    def get_facts(self, limit: int = 12) -> List[dict]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT content, category FROM facts ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [{"content": row["content"], "category": row["category"]} for row in rows]

    def remove_facts(self, phrase: str) -> int:
        value = str(phrase or "").strip()
        if not value:
            return 0
        with self._lock:
            conn = self._connect()
            cursor = conn.execute(
                "DELETE FROM facts WHERE content LIKE ? COLLATE NOCASE",
                (f"%{value}%",),
            )
            conn.commit()
            return cursor.rowcount

    def clear(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM facts")
            conn.execute("DELETE FROM conversation_summaries")
            conn.commit()
