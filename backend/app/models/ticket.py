from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.common import TicketSeverity, TicketStatus


class TicketBase(BaseModel):
    employee_id: str = Field(..., description="ID of the employee filing or associated with the ticket")
    employee_name: Optional[str] = Field(None, description="Name of the employee")
    category: str = Field(..., description="Service category e.g., Hardware, Software, Network, Access")
    title: str = Field(..., description="Concise summary of the issue")
    description: str = Field(..., description="Detailed description of the issue and context")
    severity: TicketSeverity = Field(default=TicketSeverity.MEDIUM, description="Calculated or assigned severity")
    policy_id: Optional[str] = Field(None, description="Authoritative policy identifier applied to this ticket")
    policy_citation: Optional[str] = Field(None, description="Specific clause or policy extract cited")
    tags: List[str] = Field(default_factory=list, description="Categorization or routing tags")


class TicketCreate(TicketBase):
    pass


class Ticket(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique ticket identifier e.g., TCK-2026-001")
    status: TicketStatus = Field(default=TicketStatus.OPEN, description="Current workflow status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of creation")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of last update")
    assigned_to: Optional[str] = Field(None, description="Assigned IT agent or queue")
    escalation_reason: Optional[str] = Field(None, description="Justification if escalated")
    resolution_notes: Optional[str] = Field(None, description="Notes on resolution if resolved")

