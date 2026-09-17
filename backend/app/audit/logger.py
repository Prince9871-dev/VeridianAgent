import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.models.common import AuditEventType
from backend.app.models.audit import AuditEvent


class AuditLogger:
    """Audit Logging Engine for immutable compliance traceability."""

    def __init__(self):
        self._events: List[AuditEvent] = []

    def log_event(
        self,
        event_type: AuditEventType,
        actor: str = "SYSTEM",
        session_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        action_taken: Optional[str] = None,
        policy_id: Optional[str] = None,
        policy_citation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=f"AUD-{uuid.uuid4().hex[:12].upper()}",
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            employee_id=employee_id,
            actor=actor,
            event_type=event_type,
            action_taken=action_taken,
            policy_id=policy_id,
            policy_citation=policy_citation,
            details=details or {},
        )
        self._events.append(event)
        from backend.app.db.storage import sqlite_store
        sqlite_store.append_audit_event({
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "session_id": event.session_id,
            "employee_id": event.employee_id,
            "actor": event.actor,
            "event_type": event.event_type.value,
            "action_taken": event.action_taken,
            "policy_id": event.policy_id,
            "policy_citation": event.policy_citation,
            "details": event.details,
        })
        return event


    async def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id: Optional[str] = None,
        employee_id: Optional[str] = None,
    ) -> List[AuditEvent]:
        filtered = self._events
        if session_id:
            filtered = [e for e in filtered if e.session_id == session_id]
        if employee_id:
            filtered = [e for e in filtered if e.employee_id == employee_id]
        
        # Newest first
        sorted_events = sorted(filtered, key=lambda e: e.timestamp, reverse=True)
        return sorted_events[offset : offset + limit]

    def get_events_for_session(self, session_id: str) -> List[AuditEvent]:
        """Convenience method to retrieve all events for a given session."""
        return [e for e in self._events if e.session_id == session_id]


# Global singleton instance
audit_logger = AuditLogger()
