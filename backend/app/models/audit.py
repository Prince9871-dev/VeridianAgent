from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.common import AuditEventType


class AuditEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique audit event identifier (UUID or sequential)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC event timestamp")
    session_id: Optional[str] = Field(None, description="Employee conversation session ID")
    employee_id: Optional[str] = Field(None, description="Employee ID involved")
    actor: str = Field(default="SYSTEM", description="Actor who performed the action (USER, AGENT, POLICY_ENGINE)")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    action_taken: Optional[str] = Field(None, description="Action taken (e.g. ASK_FOLLOW_UP, RESOLVE, ESCALATE)")
    policy_id: Optional[str] = Field(None, description="Policy evaluated if applicable")
    policy_citation: Optional[str] = Field(None, description="Authoritative citation text")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual payload or state transition info")

