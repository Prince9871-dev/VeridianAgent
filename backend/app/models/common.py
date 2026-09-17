from enum import Enum
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class WorkflowAction(str, Enum):
    """Authoritative workflow actions permitted in Veridian Assist."""
    ASK_FOLLOW_UP = "ASK_FOLLOW_UP"
    RESOLVE = "RESOLVE"
    ESCALATE = "ESCALATE"
    CREATE_TICKET = "CREATE_TICKET"


class TicketSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class AuditEventType(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    FOLLOW_UP_REQUESTED = "FOLLOW_UP_REQUESTED"
    REQUEST_RESOLVED = "REQUEST_RESOLVED"
    REQUEST_ESCALATED = "REQUEST_ESCALATED"
    TICKET_CREATED = "TICKET_CREATED"


class APIResponse(BaseModel, Generic[DataT]):
    """Standardized API response envelope."""
    success: bool = True
    message: str = "Success"
    data: Optional[DataT] = None
