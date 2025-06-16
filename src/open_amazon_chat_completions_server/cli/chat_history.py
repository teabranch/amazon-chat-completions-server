import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatSession:
    """Represents a chat session with history."""

    id: str
    model: str
    messages: list[dict]
    created_at: datetime
    updated_at: datetime
    name: str | None = None

    @classmethod
    def create_new(cls, model: str, name: str | None = None) -> "ChatSession":
        """Create a new chat session."""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            model=model,
            messages=[],
            created_at=now,
            updated_at=now,
            name=name,
        )

    def to_dict(self) -> dict:
        """Convert the session to a dictionary for serialization."""
        return {
            "id": self.id,
            "model": self.model,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSession":
        """Create a session from a dictionary."""
        return cls(
            id=data["id"],
            model=data["model"],
            messages=data["messages"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            name=data.get("name"),
        )


class ChatHistoryManager:
    """Manages chat session storage and retrieval."""

    def __init__(self, storage_dir: str = "~/.amazon-chat/history"):
        self.storage_dir = os.path.expanduser(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_session(self, session: ChatSession):
        """Save a chat session to disk."""
        filename = f"{session.id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        with open(filepath, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_session(self, session_id: str) -> ChatSession:
        """Load a chat session from disk."""
        filename = f"{session_id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
                return ChatSession.from_dict(data)
        except FileNotFoundError:
            raise ValueError(f"Chat session {session_id} not found")

    def list_sessions(self) -> list[ChatSession]:
        """List all available chat sessions."""
        sessions = []
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                try:
                    session = self.load_session(filename[:-5])
                    sessions.append(session)
                except (json.JSONDecodeError, ValueError):
                    continue  # Skip invalid files
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def delete_session(self, session_id: str):
        """Delete a chat session."""
        filename = f"{session_id}.json"
        filepath = os.path.join(self.storage_dir, filename)
        try:
            os.remove(filepath)
        except FileNotFoundError:
            raise ValueError(f"Chat session {session_id} not found")

    def update_session(self, session: ChatSession):
        """Update a chat session's content and timestamp."""
        session.updated_at = datetime.now()
        self.save_session(session)
