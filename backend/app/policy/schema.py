from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.common import WorkflowAction


class SourceExplicitness(str, Enum):
    EXPLICIT_POLICY = "EXPLICIT_POLICY"
    EXPLICIT_PRECEDENT = "EXPLICIT_PRECEDENT"
    ENGINEERING_FALLBACK = "ENGINEERING_FALLBACK"


class AuthoritativeRule(BaseModel):
    model_config = ConfigDict(extra="allow")
    approvals_required: List[str] = Field(default_factory=list)


class EngineeringWorkflowMapping(BaseModel):
    model_config = ConfigDict(extra="allow")
    target_queue: Optional[str] = None
    operational_status: Optional[str] = None


class AuthoritativePolicyRecord(BaseModel):
    """Derived representation of an authoritative policy rule from the DataPack PDF."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    exact_source_text: str
    source_page: int
    source_section: str
    source_citation: str
    source_explicitness: SourceExplicitness = SourceExplicitness.EXPLICIT_POLICY
    authoritative_rule: Dict[str, Any]
    engineering_workflow: Dict[str, Any]
    required_inputs: List[str] = Field(default_factory=list)


class PrecedentRecord(BaseModel):
    """Historical ticket queue precedent from Section 3 of the DataPack PDF."""
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    employee: str
    issue_summary: str
    status: str
    is_active: bool
    source_page: int = 2
    source_section: str = "Section 3: Ticket Queue"
    relevance: str


class DeterministicEvaluationResult(BaseModel):
    """
    Tripartite evaluation result separating:
    1. Authoritative Source Requirements (grounded in PDF)
    2. Historical Precedents (empirical evidence)
    3. Operational Engineering Workflow (application design)
    """
    model_config = ConfigDict(from_attributes=True)

    # 1. AUTHORITATIVE SOURCE LAYER (Grounded strictly in PDF)
    matched_policy_id: Optional[str] = Field(None, description="Policy ID from PDF if matched, or None")
    matched_policy_ids: List[str] = Field(default_factory=list, description="All policy IDs applicable")
    authoritative_source_text: Optional[str] = Field(None, description="Exact source text from PDF")
    authoritative_rule_outcome: str = Field(..., description="Pure policy outcome mandated by PDF")
    authoritative_approvals: List[str] = Field(default_factory=list, description="Approvals mandated by PDF")
    authoritative_citations: List[str] = Field(default_factory=list, description="Citations to PDF page & section")
    source_explicitness: SourceExplicitness = Field(default=SourceExplicitness.EXPLICIT_POLICY)

    # 2. HISTORICAL PRECEDENT LAYER (Historical evidence only)
    precedent_references: List[str] = Field(default_factory=list, description="Relevant ticket precedents (e.g. TK-1043)")

    # 3. OPERATIONAL ENGINEERING WORKFLOW (Application design decisions)
    workflow_action: WorkflowAction = Field(..., description="Application action: RESOLVE, ASK_FOLLOW_UP, ESCALATE, CREATE_TICKET")
    operational_status: Optional[str] = Field(None, description="Ticket status if created (e.g. PENDING_APPROVAL, OPEN)")
    operational_queue: Optional[str] = Field(None, description="Target routing queue (e.g. IT Security, Desktop Support)")
    missing_information: List[str] = Field(default_factory=list, description="Missing required inputs if action is ASK_FOLLOW_UP")
    is_engineering_fallback: bool = Field(default=False, description="True if decision is an application runtime fallback")
    fallback_type: Optional[str] = Field(None, description="NO_APPLICABLE_POLICY, INSUFFICIENT_INFORMATION, UNCLEAR_INPUT")
    user_message: str = Field(..., description="Deterministically assembled conversational response")
