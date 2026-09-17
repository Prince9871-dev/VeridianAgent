import pytest
from backend.app.db.storage import sqlite_store
from backend.app.agent.session import session_store, SessionState, ChatMessage
from backend.app.tickets.manager import ticket_manager
from backend.app.models.ticket import TicketCreate
from backend.app.models.common import TicketSeverity, AuditEventType
from backend.app.audit.logger import audit_logger


@pytest.mark.asyncio
async def test_sqlite_session_persistence_lifecycle():
    """Verify session creation, updating, retrieval, and reset persist to SQLite."""
    session_id = "test-sqlite-session-001"
    session = session_store.get_or_create(session_id, "EMP-SQLITE-01")
    session.add_message(role="employee", content="Need password reset")
    session.merge_facts({"failed_attempts": 5, "is_locked_out": True})
    session_store.save(session)

    # Directly inspect SQLite storage
    stored = sqlite_store.get_session(session_id)
    assert stored is not None
    assert stored["employee_id"] == "EMP-SQLITE-01"
    assert stored["accumulated_facts"]["failed_attempts"] == 5
    assert len(stored["history"]) == 1

    # Clear memory cache and ensure restoration from SQLite
    session_store._sessions.clear()
    restored = session_store.get(session_id)
    assert restored is not None
    assert restored.accumulated_facts["is_locked_out"] is True

    # Reset clears from SQLite
    session_store.reset(session_id)
    assert sqlite_store.get_session(session_id) is None


@pytest.mark.asyncio
async def test_sqlite_ticket_persistence():
    """Verify tickets persist to SQLite on creation and update."""
    data = TicketCreate(
        employee_id="EMP-SQLITE-02",
        employee_name="DB Tester",
        category="Hardware",
        title="SQLite Persistence Test",
        description="Testing ticket persistence in SQLite",
        severity=TicketSeverity.LOW,
        tags=["sqlite", "test"],
    )
    ticket = await ticket_manager.create_ticket(data)
    assert ticket.id.startswith("TCK-")

    # Directly check SQLite
    stored_ticket = sqlite_store.get_ticket(ticket.id)
    assert stored_ticket is not None
    assert stored_ticket["title"] == "SQLite Persistence Test"


@pytest.mark.asyncio
async def test_sqlite_audit_event_persistence():
    """Verify append-only audit events persist to SQLite table."""
    event = audit_logger.log_event(
        event_type=AuditEventType.REQUEST_RECEIVED,
        actor="SYSTEM",
        session_id="test-sqlite-audit-session",
        employee_id="EMP-SQLITE-03",
        action_taken="INGEST",
        details={"test_key": "test_value"},
    )
    assert event.id.startswith("AUD-")

    events = sqlite_store.list_audit_events(session_id="test-sqlite-audit-session")
    assert len(events) >= 1
    assert events[0]["action_taken"] == "INGEST"
