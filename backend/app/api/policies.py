from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.app.models.common import APIResponse
from backend.app.policy.schema import (
    AuthoritativePolicyRecord,
    PrecedentRecord,
    DeterministicEvaluationResult,
)
from backend.app.policy.catalog import policy_catalog
from backend.app.policy.evaluator import policy_evaluator
from backend.app.policy.fallbacks import (
    handle_no_applicable_policy,
    handle_unclear_input,
)

router = APIRouter(prefix="/policies", tags=["Policies"])


class PolicyEvaluationRequest(BaseModel):
    policy_id: Optional[str] = Field(None, description="Optional target policy ID to evaluate directly")
    category: Optional[str] = Field(None, description="Category of the request")
    raw_query: Optional[str] = Field(None, description="Employee request text")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Structured facts extracted for policy conditions")


@router.get("", response_model=APIResponse[List[AuthoritativePolicyRecord]])
async def list_policies():
    """List all authoritative Veridian Corp policies derived from Assignment_2_DataPack.pdf."""
    policies = policy_catalog.list_policies()
    return APIResponse(
        success=True,
        message=f"Retrieved {len(policies)} authoritative policies",
        data=policies,
    )


@router.get("/precedents", response_model=APIResponse[List[PrecedentRecord]])
async def list_precedents():
    """List historical ticket queue precedents from Section 3 of Assignment_2_DataPack.pdf."""
    precedents = policy_catalog.list_precedents()
    return APIResponse(
        success=True,
        message=f"Retrieved {len(precedents)} historical ticket precedents",
        data=precedents,
    )


@router.get("/{policy_id}", response_model=APIResponse[AuthoritativePolicyRecord])
async def get_policy(policy_id: str):
    """Retrieve an authoritative policy by its ID (e.g. KB-01, KB-03, POL-ASSET-01)."""
    policy = policy_catalog.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return APIResponse(
        success=True,
        message="Policy found",
        data=policy,
    )


@router.post("/evaluate", response_model=APIResponse[DeterministicEvaluationResult])
async def evaluate_policy(request: PolicyEvaluationRequest):
    """
    Deterministically evaluate a request against authoritative policy rules.
    Decoupled from LLM; pure Python rule evaluation.
    """
    pid = request.policy_id
    params = request.parameters
    raw = request.raw_query or ""

    if not pid and not raw.strip():
        result = handle_unclear_input(raw)
        return APIResponse(success=True, message="Evaluation completed", data=result)

    if pid == "KB-01":
        result = policy_evaluator.evaluate_password_reset(
            is_locked_out=params.get("is_locked_out", False),
            failed_attempts=params.get("failed_attempts"),
        )
    elif pid == "KB-02":
        result = policy_evaluator.evaluate_vpn_access(
            employment_type=params.get("employment_type", "full_time"),
            manager_approval_submitted=params.get("manager_approval_submitted", False),
            credential_age_days=params.get("credential_age_days"),
        )
    elif pid in ["KB-03", "POL-ASSET-01"]:
        result = policy_evaluator.evaluate_laptop_replacement(
            service_age_years=float(params.get("service_age_years", 0.0)),
            hardware_failure_verified=params.get("hardware_failure_verified", False),
            lead_time_days=params.get("lead_time_days"),
        )
    elif pid == "KB-04":
        result = policy_evaluator.evaluate_software_request(
            software_name=params.get("software_name", "Unknown Application"),
            in_approved_catalog=params.get("in_approved_catalog", False),
        )
    elif pid == "KB-05":
        result = policy_evaluator.evaluate_printer_issue(
            spooler_restarted=params.get("spooler_restarted", False),
            issue_persists=params.get("issue_persists", True),
            printer_asset_tag=params.get("printer_asset_tag"),
        )
    elif pid == "KB-06":
        result = policy_evaluator.evaluate_mailbox_quota(
            requested_quota_gb=float(params.get("requested_quota_gb", 25.0)),
            manager_approval=params.get("manager_approval", False),
        )
    elif pid == "KB-07":
        result = policy_evaluator.evaluate_guest_wifi()
    elif pid == "KB-08":
        result = policy_evaluator.evaluate_expense_tool(
            request_type=params.get("request_type", "technical_login"),
            account_exists=params.get("account_exists", False),
        )
    elif pid == "KB-09":
        result = policy_evaluator.evaluate_security_incident(
            incident_type=params.get("incident_type", "phishing"),
            reported_content=params.get("reported_content", ""),
            forwarded_to_others=params.get("forwarded_to_others", False),
        )
    elif pid == "KB-10":
        result = policy_evaluator.evaluate_wfh_equipment(
            remote_days_per_week=float(params.get("remote_days_per_week", 0.0)),
            equipment_type=params.get("equipment_type", "monitor"),
            manager_signoff=params.get("manager_signoff", False),
            finance_processed=params.get("finance_processed", False),
        )
    elif "admin" in raw.lower() or params.get("is_admin_access_request", False):
        result = policy_evaluator.evaluate_admin_access(
            requested_system=params.get("requested_system", "server"),
            business_justification=params.get("business_justification"),
        )
    else:
        result = handle_no_applicable_policy(raw)

    return APIResponse(success=True, message="Evaluation completed", data=result)
