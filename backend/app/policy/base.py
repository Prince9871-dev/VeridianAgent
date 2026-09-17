from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.common import WorkflowAction
from backend.app.models.request import PolicyEvaluationResult


class PolicyRule(BaseModel):
    """Definition of an authoritative policy rule."""
    id: str = Field(..., description="Unique policy identifier (e.g. POL-IT-001)")
    name: str = Field(..., description="Policy title")
    category: str = Field(..., description="Domain category e.g. Hardware, Security, Access")
    clause_text: str = Field(..., description="Authoritative policy clause text from DataPack")
    is_automated_resolvable: bool = Field(default=False)
    requires_approval: bool = Field(default=False)
    approval_role: Optional[str] = Field(None)
    sla_hours: Optional[int] = Field(None)
    escalation_triggers: List[str] = Field(default_factory=list)


class BasePolicyEngine(ABC):
    """
    Abstract Policy & Decision Engine.
    
    IMPORTANT ARCHITECTURAL BOUNDARY:
    The Policy Engine is the SOLE authority for evaluating policy compliance,
    action permissions, and mandatory escalation triggers.
    The LLM is strictly prohibited from deciding policy validity or overriding rules.
    """

    @abstractmethod
    async def get_policy_by_id(self, policy_id: str) -> Optional[PolicyRule]:
        """Retrieve an authoritative policy rule by its ID."""
        pass

    @abstractmethod
    async def find_relevant_policies(self, category: str, query: str) -> List[PolicyRule]:
        """Retrieve matching policies based on category and extracted query."""
        pass

    @abstractmethod
    async def evaluate_request(
        self,
        intent: str,
        facts: Dict[str, Any],
        policy_id: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """
        Deterministically evaluate a request against authoritative policy rules.
        Determines permitted actions, approval requirements, and escalation triggers.
        """
        pass
