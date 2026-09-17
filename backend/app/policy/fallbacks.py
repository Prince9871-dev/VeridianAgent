from typing import List, Optional
from backend.app.models.common import WorkflowAction
from backend.app.policy.schema import DeterministicEvaluationResult, SourceExplicitness
from backend.app.policy.catalog import policy_catalog


def handle_no_applicable_policy(raw_text: str) -> DeterministicEvaluationResult:
    """Application runtime fallback when no documented company policy matches the request."""
    return DeterministicEvaluationResult(
        matched_policy_id=None,
        matched_policy_ids=[],
        authoritative_source_text=None,
        authoritative_rule_outcome="NO_DOCUMENTED_POLICY",
        authoritative_approvals=[],
        authoritative_citations=[],
        source_explicitness=SourceExplicitness.ENGINEERING_FALLBACK,
        precedent_references=[],
        workflow_action=WorkflowAction.ESCALATE,
        operational_status="OPEN",
        operational_queue="IT Service Desk Manual Triage",
        missing_information=[],
        is_engineering_fallback=True,
        fallback_type="NO_APPLICABLE_POLICY",
        user_message="No documented Veridian Corp IT policy applies to this request. Routing to human IT service desk for manual assessment.",
    )


def handle_unclear_input(raw_text: str) -> DeterministicEvaluationResult:
    """Application runtime fallback when user input lacks identifiable context (e.g. REQ-15)."""
    return DeterministicEvaluationResult(
        matched_policy_id=None,
        matched_policy_ids=[],
        authoritative_source_text=None,
        authoritative_rule_outcome="UNCLEAR_INPUT",
        authoritative_approvals=[],
        authoritative_citations=[],
        source_explicitness=SourceExplicitness.ENGINEERING_FALLBACK,
        precedent_references=[],
        workflow_action=WorkflowAction.ASK_FOLLOW_UP,
        operational_status=None,
        operational_queue=None,
        missing_information=["issue_description", "affected_system_or_device"],
        is_engineering_fallback=True,
        fallback_type="UNCLEAR_INPUT",
        user_message="Could you please provide more details about what is not working, including the specific device, application, or error message?",
    )


def handle_insufficient_information(
    policy_id: str,
    missing_fields: List[str],
    prompt_message: str,
) -> DeterministicEvaluationResult:
    """Application runtime fallback when a policy applies but required parameters are missing."""
    policy = policy_catalog.get_policy(policy_id)
    source_text = policy.exact_source_text if policy else None
    citations = [policy.source_citation] if policy else []
    approvals = policy.authoritative_rule.get("approvals_required", []) if policy else []

    return DeterministicEvaluationResult(
        matched_policy_id=policy_id,
        matched_policy_ids=[policy_id] if policy_id else [],
        authoritative_source_text=source_text,
        authoritative_rule_outcome="INSUFFICIENT_INFORMATION",
        authoritative_approvals=approvals,
        authoritative_citations=citations,
        source_explicitness=SourceExplicitness.ENGINEERING_FALLBACK,
        precedent_references=[],
        workflow_action=WorkflowAction.ASK_FOLLOW_UP,
        operational_status=None,
        operational_queue=None,
        missing_information=missing_fields,
        is_engineering_fallback=True,
        fallback_type="INSUFFICIENT_INFORMATION",
        user_message=prompt_message,
    )
