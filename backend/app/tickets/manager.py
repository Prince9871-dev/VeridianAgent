import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from backend.app.models.common import TicketSeverity, TicketStatus
from backend.app.models.ticket import Ticket, TicketCreate


class TicketManager:
    """In-memory & SQLite backed ticket lifecycle manager."""

    def __init__(self):
        # Initial seed/in-memory store; will be wired to SQLite session in persistence layer
        self._tickets: Dict[str, Ticket] = {}
        self._counter: int = 1000

    def generate_ticket_id(self) -> str:
        from backend.app.db.storage import sqlite_store
        try:
            with sqlite_store._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM tickets")
                db_count = cursor.fetchone()[0]
        except Exception:
            db_count = 0
        self._counter += 1
        year = datetime.now(timezone.utc).year
        ticket_num = 1000 + db_count + self._counter
        return f"TCK-{year}-{ticket_num}"

    async def create_ticket(self, data: TicketCreate) -> Ticket:
        ticket_id = self.generate_ticket_id()
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            id=ticket_id,
            employee_id=data.employee_id,
            employee_name=data.employee_name,
            category=data.category,
            title=data.title,
            description=data.description,
            severity=data.severity,
            policy_id=data.policy_id,
            policy_citation=data.policy_citation,
            tags=data.tags,
            status=TicketStatus.OPEN,
            created_at=now,
            updated_at=now,
        )
        self._tickets[ticket_id] = ticket
        from backend.app.db.storage import sqlite_store
        sqlite_store.save_ticket({
            "id": ticket.id,
            "employee_id": ticket.employee_id,
            "employee_name": ticket.employee_name,
            "category": ticket.category,
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity.value,
            "status": ticket.status.value,
            "policy_id": ticket.policy_id,
            "policy_citation": ticket.policy_citation,
            "tags": ticket.tags,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "assigned_to": ticket.assigned_to,
            "escalation_reason": ticket.escalation_reason,
            "resolution_notes": ticket.resolution_notes,
        })
        return ticket

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        if ticket_id in self._tickets:
            return self._tickets[ticket_id]
        from backend.app.db.storage import sqlite_store
        stored = sqlite_store.get_ticket(ticket_id)
        if stored:
            ticket = Ticket(
                id=stored["id"],
                employee_id=stored["employee_id"],
                employee_name=stored["employee_name"],
                category=stored["category"],
                title=stored["title"],
                description=stored["description"],
                severity=TicketSeverity(stored["severity"]),
                status=TicketStatus(stored["status"]),
                policy_id=stored.get("policy_id"),
                policy_citation=stored.get("policy_citation"),
                tags=stored.get("tags", []),
                created_at=datetime.fromisoformat(stored["created_at"]),
                updated_at=datetime.fromisoformat(stored["updated_at"]),
                assigned_to=stored.get("assigned_to"),
                escalation_reason=stored.get("escalation_reason"),
                resolution_notes=stored.get("resolution_notes"),
            )
            self._tickets[ticket_id] = ticket
            return ticket
        return None

    async def list_tickets(self, limit: int = 50, offset: int = 0) -> List[Ticket]:
        items = list(self._tickets.values())
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update_status(
        self,
        ticket_id: str,
        status: TicketStatus,
        notes: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> Optional[Ticket]:
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        ticket.status = status
        ticket.updated_at = datetime.now(timezone.utc)
        if notes:
            ticket.resolution_notes = notes
        if escalation_reason:
            ticket.escalation_reason = escalation_reason
        from backend.app.db.storage import sqlite_store
        sqlite_store.save_ticket({
            "id": ticket.id,
            "employee_id": ticket.employee_id,
            "employee_name": ticket.employee_name,
            "category": ticket.category,
            "title": ticket.title,
            "description": ticket.description,
            "severity": ticket.severity.value,
            "status": ticket.status.value,
            "policy_id": ticket.policy_id,
            "policy_citation": ticket.policy_citation,
            "tags": ticket.tags,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "assigned_to": ticket.assigned_to,
            "escalation_reason": ticket.escalation_reason,
            "resolution_notes": ticket.resolution_notes,
        })
        return ticket



# Global singleton manager instance for application lifecycle
ticket_manager = TicketManager()
