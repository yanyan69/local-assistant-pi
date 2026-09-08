import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from .app_config import CONVERSATIONS_DIR

DEFAULT_CONVERSATIONS_DIR = CONVERSATIONS_DIR


class ConversationStore:
    """File-backed chat transcripts kept separate from durable assistant memory."""

    def __init__(self, directory: str = str(DEFAULT_CONVERSATIONS_DIR)):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, conversation_id: str) -> Path:
        if not conversation_id or Path(conversation_id).name != conversation_id:
            raise ValueError("Invalid conversation id")
        return self.directory / f"{conversation_id}.json"

    def create(self, title: str = "New chat") -> Dict:
        now = datetime.now(timezone.utc).isoformat()
        conversation = {
            "id": uuid.uuid4().hex,
            "title": (title or "New chat").strip()[:80] or "New chat",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        self._write(conversation)
        return conversation

    def get(self, conversation_id: str) -> Optional[Dict]:
        try:
            path = self._path(conversation_id)
        except ValueError:
            return None
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (OSError, ValueError):
                return None

    def list(self) -> List[Dict]:
        conversations = []
        with self._lock:
            for path in self.directory.glob("*.json"):
                conversation = self.get(path.stem)
                if conversation:
                    conversations.append({key: conversation.get(key) for key in ("id", "title", "created_at", "updated_at")})
        return sorted(conversations, key=lambda item: item.get("updated_at", ""), reverse=True)

    def append(self, conversation_id: str, role: str, content: str) -> Optional[Dict]:
        conversation = self.get(conversation_id)
        if not conversation or role not in {"user", "assistant"} or not str(content or "").strip():
            return conversation
        now = datetime.now(timezone.utc).isoformat()
        conversation.setdefault("messages", []).append({
            "role": role,
            "content": str(content).strip(),
            "created_at": now,
        })
        if role == "user" and conversation.get("title") == "New chat":
            conversation["title"] = str(content).strip()[:80]
        conversation["updated_at"] = now
        self._write(conversation)
        return conversation

    def _write(self, conversation: Dict) -> None:
        path = self._path(conversation["id"])
        temporary_path = path.with_suffix(".json.tmp")
        with self._lock:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(conversation, handle, ensure_ascii=True, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
