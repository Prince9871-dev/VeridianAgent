from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.common import WorkflowAction, TicketSeverity
from backend.app.models.ticket import Ticket


class EmployeeMessage(BaseModel):
    session_id: str = Field(..., description="Unique conversation session ID")
    employee_id: str = Field(..., description="Veridian Corp Employee ID")
    content: str = Field(..., description="Natural language message from the employee")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Client or context metadata")


class IntentAnalysis(BaseModel):
    """Output of LLM Intent Classification & Fact Extraction (LLM responsibility)."""
    raw_intent: str = Field(..., description="Identified intent label")
    extracted_facts: Dict[str, Any] = Field(default_factory=dict, description="Key parameters extracted from prompt")
    missing_fields: List[str] = Field(default_factory=list, description="Required parameters missing from the request")
    confidence: float = Field(default=1.0, description="Confidence score of classification")


class PolicyEvaluationResult(BaseModel):
    """Output of Authoritative Policy Engine (Deterministic rule responsibility)."""
    policy_id: Optional[str] = Field(None, description="Authoritative policy ID")
    policy_name: Optional[str] = Field(None, description="Title of the authoritative policy")
    clause_cited: Optional[str] = Field(None, description="Exact policy extract or clause")
    is_permitted: bool = Field(..., description="Whether the requested action is permitted by policy")
    requires_approval: bool = Field(default=False, description="Whether human approval is required")
    escalation_required: bool = Field(default=False, description="Whether escalation is required")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation under policy")


class ServiceAgentResponse(BaseModel):
    """Full coordinated response returned to the employee."""
    session_id: str
    message: str = Field(..., description="Natural language response to the employee")
    action: WorkflowAction = Field(..., description="Workflow action determined by the system")
    intent_analysis: Optional[IntentAnalysis] = None
    policy_evaluation: Optional[PolicyEvaluationResult] = None
    follow_up_question: Optional[str] = None
    ticket: Optional[Ticket] = None
    source_citation: Optional[str] = Field(None, description="Authoritative source citation displayed to user")
    audit_event_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
