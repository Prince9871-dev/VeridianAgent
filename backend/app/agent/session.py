from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str = Field(..., description="Role: employee or agent")
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    """Multi-turn session dialogue state and accumulated factual context."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    employee_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[ChatMessage] = Field(default_factory=list)
    accumulated_facts: Dict[str, Any] = Field(default_factory=dict)
    active_policy_id: Optional[str] = None
    pending_missing_fields: List[str] = Field(default_factory=list)
    is_concluded: bool = False

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message chronologically to the conversation history."""
        self.history.append(
            ChatMessage(
                role=role,
                content=content,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {},
            )
        )
        self.updated_at = datetime.now(timezone.utc)

    def merge_facts(self, new_facts: Dict[str, Any]) -> None:
        """
        Safely merge newly extracted facts into accumulated facts.
        Adds or updates fields without accidentally removing previously established facts.
        """
        for key, value in new_facts.items():
            if value is not None:
                self.accumulated_facts[key] = value
        self.updated_at = datetime.now(timezone.utc)


from backend.app.db.storage import sqlite_store


class SessionStore:
    """SQLite-backed multi-turn session manager with in-memory caching."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str, employee_id: str = "EMP-UNKNOWN") -> SessionState:
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Check SQLite store
        stored = sqlite_store.get_session(session_id)
        if stored:
            session = self._reconstruct_session(stored)
            self._sessions[session_id] = session
            return session

        new_session = SessionState(
            session_id=session_id,
            employee_id=employee_id,
        )
        self.save(new_session)
        return new_session

    def get(self, session_id: str) -> Optional[SessionState]:
        if session_id in self._sessions:
            return self._sessions[session_id]

        stored = sqlite_store.get_session(session_id)
        if stored:
            session = self._reconstruct_session(stored)
            self._sessions[session_id] = session
            return session

        return None

    def save(self, session: SessionState) -> None:
        self._sessions[session.session_id] = session
        sqlite_store.save_session({
            "session_id": session.session_id,
            "employee_id": session.employee_id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "history": [m.model_dump(mode="json") for m in session.history],
            "accumulated_facts": session.accumulated_facts,
            "active_policy_id": session.active_policy_id,
            "pending_missing_fields": session.pending_missing_fields,
            "is_concluded": session.is_concluded,
        })

    def reset(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
        sqlite_store.delete_session(session_id)

    def _reconstruct_session(self, data: Dict[str, Any]) -> SessionState:
        history = [
            ChatMessage(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]) if isinstance(m["timestamp"], str) else m["timestamp"],
                metadata=m.get("metadata", {}),
            )
            for m in data.get("history", [])
        ]
        created = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        updated = datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"]
        return SessionState(
            session_id=data["session_id"],
            employee_id=data["employee_id"],
            created_at=created,
            updated_at=updated,
            history=history,
            accumulated_facts=data.get("accumulated_facts", {}),
            active_policy_id=data.get("active_policy_id"),
            pending_missing_fields=data.get("pending_missing_fields", []),
            is_concluded=data.get("is_concluded", False),
        )


# Global singleton session store
session_store = SessionStore()
