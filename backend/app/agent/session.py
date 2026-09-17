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


class SessionStore:
    """In-memory session manager with lifecycle methods."""

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str, employee_id: str = "EMP-UNKNOWN") -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                employee_id=employee_id,
            )
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def save(self, session: SessionState) -> None:
        self._sessions[session.session_id] = session

    def reset(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]


# Global singleton session store
session_store = SessionStore()
