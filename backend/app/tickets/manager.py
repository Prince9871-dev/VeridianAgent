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
        self._counter += 1
        return f"TCK-{datetime.now(timezone.utc).year}-{self._counter}"

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
        return ticket

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self._tickets.get(ticket_id)

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
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        ticket.status = status
        ticket.updated_at = datetime.now(timezone.utc)
        if notes:
            ticket.resolution_notes = notes
        if escalation_reason:
            ticket.escalation_reason = escalation_reason
        return ticket



# Global singleton manager instance for application lifecycle
ticket_manager = TicketManager()
