from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.models.common import APIResponse, TicketStatus
from backend.app.models.ticket import Ticket, TicketCreate
from backend.app.tickets.manager import ticket_manager

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=APIResponse[Ticket])
async def create_ticket(ticket_data: TicketCreate):
    """Create a structured IT support ticket."""
    created = await ticket_manager.create_ticket(ticket_data)
    return APIResponse(
        success=True,
        message=f"Ticket {created.id} created successfully",
        data=created,
    )


@router.get("", response_model=APIResponse[List[Ticket]])
async def list_tickets(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List structured tickets with pagination."""
    tickets = await ticket_manager.list_tickets(limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(tickets)} tickets",
        data=tickets,
    )


@router.get("/{ticket_id}", response_model=APIResponse[Ticket])
async def get_ticket(ticket_id: str):
    """Retrieve details for a specific ticket."""
    ticket = await ticket_manager.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    return APIResponse(
        success=True,
        message="Ticket found",
        data=ticket,
    )
