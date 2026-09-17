from typing import Any, Dict, List, Optional
from backend.app.models.common import WorkflowAction
from backend.app.policy.schema import (
    DeterministicEvaluationResult,
    SourceExplicitness,
)
from backend.app.policy.catalog import policy_catalog
from backend.app.policy.fallbacks import (
    handle_no_applicable_policy,
    handle_unclear_input,
    handle_insufficient_information,
)


class PolicyEvaluator:
    """
    Pure Python deterministic policy evaluation engine.
    
    Guarantees that:
    1. The LLM has zero policy authority.
    2. Policy rules (eligibility, caps, approvals) are evaluated deterministically.
    3. Operational engineering workflows (RESOLVE, CREATE_TICKET, etc.) are strictly separated from source rules.
    4. Evaluator results clearly distinguish source requirements, precedents, and operational state.
    """

    def evaluate_password_reset(
        self,
        is_locked_out: bool,
        failed_attempts: Optional[int] = None,
    ) -> DeterministicEvaluationResult:
        """KB-01: Password Reset."""
        policy = policy_catalog.get_policy("KB-01")
        precedent = policy_catalog.get_precedent("TK-1049")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        if is_locked_out:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-01",
                matched_policy_ids=["KB-01"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="LOCKED_OUT_MANUAL_UNLOCK_REQUIRED",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.CREATE_TICKET,
                operational_status="OPEN",
                operational_queue="IT Service Desk",
                user_message="Under Policy KB-01, accounts locked out after 5 failed attempts require manual IT unlock. I have opened an IT support ticket for manual account unlock. No approval is required.",
            )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-01",
                matched_policy_ids=["KB-01"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="SELF_SERVICE_RESET_PERMITTED",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                operational_status=None,
                operational_queue=None,
                user_message="Under Policy KB-01, employees can reset their own password via the self-service portal at any time. No approval is required.",
            )

    def evaluate_vpn_access(
        self,
        employment_type: str,
        manager_approval_submitted: bool = False,
        credential_age_days: Optional[int] = None,
    ) -> DeterministicEvaluationResult:
        """KB-02: VPN Access."""
        policy = policy_catalog.get_policy("KB-02")
        precedent = policy_catalog.get_precedent("TK-1042")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []
        norm_type = employment_type.lower().replace("-", "_").strip()

        if norm_type in ["full_time", "fulltime", "employee"]:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-02",
                matched_policy_ids=["KB-02"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="AUTOMATIC_VPN_ACCESS_GRANTED",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-02, VPN access is granted automatically to all full-time employees. VPN credentials expire every 90 days and must be renewed by the employee via the self-service portal.",
            )
        elif norm_type in ["contractor", "external"]:
            if manager_approval_submitted:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-02",
                    matched_policy_ids=["KB-02"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="CONTRACTOR_VPN_APPROVAL_VERIFIED",
                    authoritative_approvals=["Manager approval submitted via access request form (contractors only)"],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.CREATE_TICKET,
                    operational_status="PENDING_FULFILLMENT",
                    operational_queue="Network Operations",
                    user_message="Under Policy KB-02, manager approval via the access request form is verified. A ticket has been created for contractor VPN provisioning.",
                )
            else:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-02",
                    matched_policy_ids=["KB-02"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="CONTRACTOR_VPN_REQUIRES_MANAGER_APPROVAL",
                    authoritative_approvals=["Manager approval submitted via access request form (contractors only)"],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.ASK_FOLLOW_UP,
                    missing_information=["manager_approval_form_status"],
                    user_message="Under Policy KB-02, contractors require manager approval submitted via the access request form. Please confirm if your manager has submitted the form.",
                )
        else:
            return handle_insufficient_information(
                "KB-02",
                ["employment_type"],
                "Under Policy KB-02, VPN access rules differ for full-time employees and contractors. Please specify whether this is for a full-time employee or a contractor.",
            )

    def evaluate_laptop_replacement(
        self,
        service_age_years: float,
        hardware_failure_verified: bool = False,
        lead_time_days: Optional[int] = None,
        is_repair_request: bool = False,
    ) -> DeterministicEvaluationResult:
        """KB-03 and POL-ASSET-01: Laptop Replacement & Lifecycle."""
        kb03 = policy_catalog.get_policy("KB-03")
        asset_policy = policy_catalog.get_policy("POL-ASSET-01")
        precedent = policy_catalog.get_precedent("TK-1043")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        citations = []
        if kb03:
            citations.append(kb03.source_citation)
        if asset_policy:
            citations.append(asset_policy.source_citation)

        # Check KB-03 Advance Notice Requirement (strictly enforced, no waiver)
        if lead_time_days is not None and lead_time_days < 14:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-03",
                matched_policy_ids=["KB-03"],
                authoritative_source_text=kb03.exact_source_text if kb03 else None,
                authoritative_rule_outcome="ADVANCE_NOTICE_MINIMUM_UNMET",
                authoritative_approvals=[],
                authoritative_citations=citations,
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.ASK_FOLLOW_UP,
                missing_information=["replacement_date_lead_time"],
                user_message="Under Policy KB-03, laptop replacement requests must be raised at least 2 weeks in advance of intended replacement. Please confirm your planned replacement timeline.",
            )

        # Check KB-03 Service Eligibility
        is_eligible_kb03 = (service_age_years >= 3.0) or hardware_failure_verified

        if not is_eligible_kb03:
            if is_repair_request:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-03",
                    matched_policy_ids=["KB-03", "POL-ASSET-01"],
                    authoritative_source_text=kb03.exact_source_text if kb03 else None,
                    authoritative_rule_outcome="INELIGIBLE_FOR_REPLACEMENT_ROUTED_TO_REPAIR_TRIAGE",
                    authoritative_approvals=[],
                    authoritative_citations=citations,
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.CREATE_TICKET,
                    operational_status="OPEN",
                    operational_queue="Hardware Repair / Triage",
                    user_message="Under Policy KB-03, laptops under 3 years are not eligible for replacement without verified hardware failure. A hardware repair triage ticket has been created for your screen issue.",
                )
            return DeterministicEvaluationResult(
                matched_policy_id="KB-03",
                matched_policy_ids=["KB-03", "POL-ASSET-01"],
                authoritative_source_text=kb03.exact_source_text if kb03 else None,
                authoritative_rule_outcome="INELIGIBLE_UNDER_KB03",
                authoritative_approvals=[],
                authoritative_citations=citations,
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-03, laptops are eligible for replacement after 3 years of service, or earlier in case of verified hardware failure. A repair triage ticket can be created if there is a hardware malfunction.",
            )

        # Eligible under KB-03: Evaluate Asset Management Policy refresh cycle
        if service_age_years < 4.0:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-03",
                matched_policy_ids=["KB-03", "POL-ASSET-01"],
                authoritative_source_text=f"{kb03.exact_source_text} | {asset_policy.exact_source_text}" if (kb03 and asset_policy) else None,
                authoritative_rule_outcome="ELIGIBLE_EARLY_REPLACEMENT_REQUIRES_FINANCE_SIGNOFF_AND_IT_APPROVAL",
                authoritative_approvals=["Finance sign-off", "IT approval"],
                authoritative_citations=citations,
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.CREATE_TICKET,
                operational_status="PENDING_APPROVAL",
                operational_queue="Finance & Asset Management",
                user_message="Under Policy KB-03, your laptop is eligible for replacement. In accordance with the Asset Management Policy, because replacement occurs outside the standard 4-year refresh cycle, Finance sign-off in addition to IT approval is required before fulfillment.",
            )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-03",
                matched_policy_ids=["KB-03", "POL-ASSET-01"],
                authoritative_source_text=f"{kb03.exact_source_text} | {asset_policy.exact_source_text}" if (kb03 and asset_policy) else None,
                authoritative_rule_outcome="STANDARD_REFRESH_CYCLE_REACHED",
                authoritative_approvals=["IT approval"],
                authoritative_citations=citations,
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.CREATE_TICKET,
                operational_status="PENDING_FULFILLMENT",
                operational_queue="Hardware Fulfillment",
                user_message="Under Policy KB-03 and the Asset Management Policy, your laptop has reached the standard 4-year refresh cycle. A ticket has been created for standard replacement.",
            )

    def evaluate_software_request(
        self,
        software_name: str,
        in_approved_catalog: bool,
    ) -> DeterministicEvaluationResult:
        """KB-04: Software Installation Requests."""
        policy = policy_catalog.get_policy("KB-04")
        precedent = policy_catalog.get_precedent("TK-1044")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        if in_approved_catalog:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-04",
                matched_policy_ids=["KB-04"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="CATALOG_SOFTWARE_SELF_INSTALL_PERMITTED",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message=f"Under Policy KB-04, {software_name} is listed in the approved software catalog and can be self-installed directly.",
            )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-04",
                matched_policy_ids=["KB-04"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="NON_CATALOG_SOFTWARE_REQUIRES_SECURITY_REVIEW",
                authoritative_approvals=["IT Security review (non-catalog software only)"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.CREATE_TICKET,
                operational_status="PENDING_SECURITY_REVIEW",
                operational_queue="IT Security",
                user_message=f"Under Policy KB-04, {software_name} is not in the software catalog and requires IT Security review, which takes 3–5 business days. A review ticket has been created.",
            )

    def evaluate_printer_issue(
        self,
        spooler_restarted: bool = False,
        issue_persists: bool = True,
        printer_asset_tag: Optional[str] = None,
    ) -> DeterministicEvaluationResult:
        """KB-05: Printer Troubleshooting."""
        policy = policy_catalog.get_policy("KB-05")
        precedent = policy_catalog.get_precedent("TK-1046")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        if issue_persists:
            if not printer_asset_tag:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-05",
                    matched_policy_ids=["KB-05"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="MISSING_PRINTER_ASSET_TAG",
                    authoritative_approvals=[],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.ASK_FOLLOW_UP,
                    missing_information=["printer_asset_tag"],
                    user_message="Under Policy KB-05, for printer issues, please first check the printer queue and restart the print spooler. If the issue persists, please provide the printer’s asset tag so a support ticket can be logged.",
                )
            else:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-05",
                    matched_policy_ids=["KB-05"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="PRINTER_TICKET_LOGGED_WITH_ASSET_TAG",
                    authoritative_approvals=[],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.CREATE_TICKET,
                    operational_status="OPEN",
                    operational_queue="Desktop Support",
                    user_message=f"Under Policy KB-05, a service ticket has been created for printer asset tag {printer_asset_tag}.",
                )
        elif not spooler_restarted:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-05",
                matched_policy_ids=["KB-05"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="INITIAL_PRINTER_TROUBLESHOOTING_STEP",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-05, for printer issues, please first check the printer queue and restart the print spooler. If the issue persists, contact us with the printer's asset tag.",
            )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-05",
                matched_policy_ids=["KB-05"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="PRINTER_ISSUE_RESOLVED_AFTER_RESTART",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-05, print spooler restart completed successfully.",
            )

    def evaluate_mailbox_quota(
        self,
        requested_quota_gb: float,
        manager_approval: bool = False,
    ) -> DeterministicEvaluationResult:
        """KB-06: Email Mailbox Quota."""
        policy = policy_catalog.get_policy("KB-06")
        precedent = policy_catalog.get_precedent("TK-1045")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        if requested_quota_gb <= 25.0:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-06",
                matched_policy_ids=["KB-06"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="WITHIN_DEFAULT_QUOTA",
                authoritative_approvals=[],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-06, default mailbox quota is 25GB. Employees nearing quota should archive old mail.",
            )
        elif requested_quota_gb <= 50.0:
            if manager_approval:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-06",
                    matched_policy_ids=["KB-06"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="QUOTA_INCREASE_APPROVED",
                    authoritative_approvals=["Manager approval (for increases beyond 25GB)"],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.CREATE_TICKET,
                    operational_status="PENDING_FULFILLMENT",
                    operational_queue="IT Operations",
                    user_message=f"Under Policy KB-06, your mailbox quota increase to {requested_quota_gb}GB with manager approval has been submitted for fulfillment.",
                )
            else:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-06",
                    matched_policy_ids=["KB-06"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="MANAGER_APPROVAL_REQUIRED_FOR_QUOTA_INCREASE",
                    authoritative_approvals=["Manager approval (for increases beyond 25GB)"],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=precedent_refs,
                    workflow_action=WorkflowAction.CREATE_TICKET,
                    operational_status="PENDING_MANAGER_APPROVAL",
                    operational_queue="IT Operations",
                    user_message=f"Under Policy KB-06, quota increases beyond 25GB require manager approval. A ticket has been created pending manager sign-off.",
                )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-06",
                matched_policy_ids=["KB-06"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="CANNOT_BE_INCREASED_UNDER_50GB_POLICY_CAP",
                authoritative_approvals=["Manager approval (for increases beyond 25GB)"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-06, quota increases beyond 25GB require manager approval and are capped at 50GB. Increases exceeding 50GB cannot be granted under policy.",
            )

    def evaluate_guest_wifi(self) -> DeterministicEvaluationResult:
        """KB-07: Guest Wi-Fi Access."""
        policy = policy_catalog.get_policy("KB-07")
        precedent = policy_catalog.get_precedent("TK-1051")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        return DeterministicEvaluationResult(
            matched_policy_id="KB-07",
            matched_policy_ids=["KB-07"],
            authoritative_source_text=policy.exact_source_text if policy else None,
            authoritative_rule_outcome="SELF_SERVICE_GUEST_WIFI_NO_TICKET_REQUIRED",
            authoritative_approvals=[],
            authoritative_citations=[policy.source_citation] if policy else [],
            source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
            precedent_references=precedent_refs,
            workflow_action=WorkflowAction.RESOLVE,
            user_message="Under Policy KB-07, guest Wi-Fi credentials are valid for 24 hours and can be generated by any employee from the front-desk kiosk. No IT ticket is required.",
        )

    def evaluate_expense_tool(
        self,
        request_type: str,
        account_exists: bool = False,
    ) -> DeterministicEvaluationResult:
        """KB-08: Expense Software Access."""
        policy = policy_catalog.get_policy("KB-08")
        norm_req = request_type.lower().strip()

        if norm_req in ["grant_access", "provision_account", "new_account"]:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-08",
                matched_policy_ids=["KB-08"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="ACCESS_GRANTED_BY_FINANCE_NOT_IT",
                authoritative_approvals=["Granted by Finance, not IT"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=[],
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-08, access to the expense management tool is granted by Finance, not IT. Please contact Finance directly for account provisioning.",
            )
        else:
            if account_exists:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-08",
                    matched_policy_ids=["KB-08"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="IT_ASSISTS_EXISTING_EXPENSE_ACCOUNT",
                    authoritative_approvals=[],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=[],
                    workflow_action=WorkflowAction.ASK_FOLLOW_UP,
                    missing_information=["screenshot_or_error_details"],
                    user_message="Under Policy KB-08, IT can assist with login/technical issues once an account already exists. Please provide a screenshot or the exact error message.",
                )
            else:
                return DeterministicEvaluationResult(
                    matched_policy_id="KB-08",
                    matched_policy_ids=["KB-08"],
                    authoritative_source_text=policy.exact_source_text if policy else None,
                    authoritative_rule_outcome="ACCOUNT_MUST_EXIST_BEFORE_IT_ASSISTS",
                    authoritative_approvals=["Granted by Finance, not IT"],
                    authoritative_citations=[policy.source_citation] if policy else [],
                    source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                    precedent_references=[],
                    workflow_action=WorkflowAction.RESOLVE,
                    user_message="Under Policy KB-08, IT can only assist with login/technical issues once an account already exists. If your account has not been set up, please request access from Finance.",
                )

    def evaluate_security_incident(
        self,
        incident_type: str = "phishing",
        reported_content: str = "",
        forwarded_to_others: bool = False,
    ) -> DeterministicEvaluationResult:
        """KB-09: Security Incident Reporting."""
        policy = policy_catalog.get_policy("KB-09")
        precedent = policy_catalog.get_precedent("TK-1048")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        warning_note = " Please note that under Policy KB-09, suspicious emails must NOT be forwarded to other employees." if forwarded_to_others else ""

        return DeterministicEvaluationResult(
            matched_policy_id="KB-09",
            matched_policy_ids=["KB-09"],
            authoritative_source_text=policy.exact_source_text if policy else None,
            authoritative_rule_outcome="MANDATORY_REPORT_TO_SECURITY_DO_NOT_FORWARD",
            authoritative_approvals=["IT Security escalation"],
            authoritative_citations=[policy.source_citation] if policy else [],
            source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
            precedent_references=precedent_refs,
            workflow_action=WorkflowAction.ESCALATE,
            operational_status="ESCALATED_UNDER_INVESTIGATION",
            operational_queue="Security Operations",
            user_message=f"Under Policy KB-09, any suspected phishing email, malware, or unauthorized access attempt must be reported to security@veridian-corp.example immediately and should not be forwarded to other employees.{warning_note} I have auto-flagged and escalated this incident to IT Security.",
        )

    def evaluate_wfh_equipment(
        self,
        remote_days_per_week: float,
        equipment_type: str = "monitor",
        manager_signoff: bool = False,
        finance_processed: bool = False,
    ) -> DeterministicEvaluationResult:
        """KB-10: Work-From-Home Equipment."""
        policy = policy_catalog.get_policy("KB-10")
        precedent = policy_catalog.get_precedent("TK-1047")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []
        norm_equip = equipment_type.lower().strip()

        # Boundary check: "more than 3 days/week"
        if remote_days_per_week <= 3.0:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-10",
                matched_policy_ids=["KB-10"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="INELIGIBLE_UNDER_REMOTE_WORK_THRESHOLD",
                authoritative_approvals=["Manager sign-off", "Finance processing"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message="Under Policy KB-10, employees working remotely more than 3 days/week are eligible for a one-time home office equipment allowance (chair, monitor).",
            )

        if norm_equip not in ["chair", "monitor"]:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-10",
                matched_policy_ids=["KB-10"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="EQUIPMENT_OUTSIDE_ALLOWANCE_SCOPE",
                authoritative_approvals=["Manager sign-off", "Finance processing"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message=f"Under Policy KB-10, the one-time equipment allowance covers a chair or monitor only. {equipment_type} is not eligible under this policy.",
            )

        if not (manager_signoff and finance_processed):
            return DeterministicEvaluationResult(
                matched_policy_id="KB-10",
                matched_policy_ids=["KB-10"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="PENDING_MANAGER_SIGNOFF_AND_FINANCE_PROCESSING",
                authoritative_approvals=["Manager sign-off", "Finance processing"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.RESOLVE,
                user_message=f"Under Policy KB-10, you are eligible for a home office {norm_equip}. However, this requires manager sign-off and Finance processing. IT only handles the equipment shipping request once approved.",
            )
        else:
            return DeterministicEvaluationResult(
                matched_policy_id="KB-10",
                matched_policy_ids=["KB-10"],
                authoritative_source_text=policy.exact_source_text if policy else None,
                authoritative_rule_outcome="APPROVED_FOR_EQUIPMENT_SHIPPING",
                authoritative_approvals=["Manager sign-off", "Finance processing"],
                authoritative_citations=[policy.source_citation] if policy else [],
                source_explicitness=SourceExplicitness.EXPLICIT_POLICY,
                precedent_references=precedent_refs,
                workflow_action=WorkflowAction.CREATE_TICKET,
                operational_status="PENDING_SHIPPING",
                operational_queue="IT Logistics",
                user_message=f"Under Policy KB-10, manager sign-off and Finance processing have been confirmed. An equipment shipping ticket has been created for your {norm_equip}.",
            )

    def evaluate_admin_access(
        self,
        requested_system: str,
        business_justification: Optional[str] = None,
    ) -> DeterministicEvaluationResult:
        """Historical precedent TK-1050: Admin access request."""
        precedent = policy_catalog.get_precedent("TK-1050")
        precedent_refs = [f"{precedent.ticket_id} ({precedent.employee}: {precedent.issue_summary} - {precedent.status})"] if precedent else []

        return DeterministicEvaluationResult(
            matched_policy_id=None,
            matched_policy_ids=[],
            authoritative_source_text=None,
            authoritative_rule_outcome="NO_POLICY_FOR_UNRESTRICTED_ADMIN_ACCESS",
            authoritative_approvals=[],
            authoritative_citations=[],
            source_explicitness=SourceExplicitness.EXPLICIT_PRECEDENT,
            precedent_references=precedent_refs,
            workflow_action=WorkflowAction.CREATE_TICKET,
            operational_status="PENDING_REVIEW",
            operational_queue="IT Security / System Administration",
            user_message=f"Veridian Corp IT knowledge-base policies do not authorize self-service administrative access to {requested_system}. Historical precedent TK-1050 demonstrates that admin access requests without business justification are rejected. A ticket has been routed to IT Security for review.",
        )


# Global singleton instance
policy_evaluator = PolicyEvaluator()
