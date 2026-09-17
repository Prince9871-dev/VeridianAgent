import pytest
from backend.app.models.common import WorkflowAction
from backend.app.policy.evaluator import policy_evaluator
from backend.app.policy.schema import SourceExplicitness


# --- KB-01: Password Reset Lockout ---
def test_kb01_unlocked_allows_self_service():
    result = policy_evaluator.evaluate_password_reset(is_locked_out=False, failed_attempts=4)
    assert result.authoritative_rule_outcome == "SELF_SERVICE_RESET_PERMITTED"
    assert result.workflow_action == WorkflowAction.RESOLVE
    assert len(result.authoritative_approvals) == 0
    assert result.source_explicitness == SourceExplicitness.EXPLICIT_POLICY


def test_kb01_locked_out_requires_manual_unlock():
    result = policy_evaluator.evaluate_password_reset(is_locked_out=True, failed_attempts=6)
    assert result.authoritative_rule_outcome == "LOCKED_OUT_MANUAL_UNLOCK_REQUIRED"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "OPEN"
    assert result.operational_queue == "IT Service Desk"
    assert "TK-1049" in result.precedent_references[0]


# --- KB-02: VPN Access ---
def test_kb02_full_time_automatic_grant():
    result = policy_evaluator.evaluate_vpn_access(employment_type="full_time")
    assert result.authoritative_rule_outcome == "AUTOMATIC_VPN_ACCESS_GRANTED"
    assert result.workflow_action == WorkflowAction.RESOLVE
    assert "TK-1042" in result.precedent_references[0]


def test_kb02_contractor_requires_approval_form():
    result = policy_evaluator.evaluate_vpn_access(employment_type="contractor", manager_approval_submitted=False)
    assert result.authoritative_rule_outcome == "CONTRACTOR_VPN_REQUIRES_MANAGER_APPROVAL"
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP
    assert "Manager approval" in result.authoritative_approvals[0]


def test_kb02_contractor_with_approval_verified():
    result = policy_evaluator.evaluate_vpn_access(employment_type="contractor", manager_approval_submitted=True)
    assert result.authoritative_rule_outcome == "CONTRACTOR_VPN_APPROVAL_VERIFIED"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_FULFILLMENT"


# --- KB-03 and POL-ASSET-01: Laptop Replacement & 4-Year Cycle ---
def test_kb03_laptop_under_3_years_ineligible():
    result = policy_evaluator.evaluate_laptop_replacement(service_age_years=2.0, hardware_failure_verified=False)
    assert result.authoritative_rule_outcome == "INELIGIBLE_UNDER_KB03"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb03_notice_window_under_14_days_unmet():
    """Notice requirement applies as written: no waiver for hardware failure."""
    result = policy_evaluator.evaluate_laptop_replacement(service_age_years=3.5, hardware_failure_verified=True, lead_time_days=10)
    assert result.authoritative_rule_outcome == "ADVANCE_NOTICE_MINIMUM_UNMET"
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP
    assert "replacement_date_lead_time" in result.missing_information


def test_kb03_exact_3_years_requires_dual_approval_under_asset_policy():
    """Laptops >= 3.0 yrs eligible under KB-03, but < 4.0 yrs require Finance + IT approval per Asset Policy."""
    result = policy_evaluator.evaluate_laptop_replacement(service_age_years=3.0, lead_time_days=14)
    assert result.authoritative_rule_outcome == "ELIGIBLE_EARLY_REPLACEMENT_REQUIRES_FINANCE_SIGNOFF_AND_IT_APPROVAL"
    assert "Finance sign-off" in result.authoritative_approvals
    assert "IT approval" in result.authoritative_approvals
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_APPROVAL"
    assert "TK-1043" in result.precedent_references[0]


def test_kb03_precedent_3_point_2_years():
    """Matches TK-1043 precedent (S. Iyer, 3.2 yrs old, Approved)."""
    result = policy_evaluator.evaluate_laptop_replacement(service_age_years=3.2, lead_time_days=14)
    assert result.authoritative_rule_outcome == "ELIGIBLE_EARLY_REPLACEMENT_REQUIRES_FINANCE_SIGNOFF_AND_IT_APPROVAL"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET


def test_asset_policy_4_years_refresh_standard():
    """At 4.0 yrs, standard refresh cycle reached."""
    result = policy_evaluator.evaluate_laptop_replacement(service_age_years=4.0, lead_time_days=14)
    assert result.authoritative_rule_outcome == "STANDARD_REFRESH_CYCLE_REACHED"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_FULFILLMENT"


# --- KB-04: Software Requests ---
def test_kb04_catalog_software_self_install():
    result = policy_evaluator.evaluate_software_request(software_name="VS Code", in_approved_catalog=True)
    assert result.authoritative_rule_outcome == "CATALOG_SOFTWARE_SELF_INSTALL_PERMITTED"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb04_non_catalog_software_requires_security_review():
    result = policy_evaluator.evaluate_software_request(software_name="Custom Data Tool", in_approved_catalog=False)
    assert result.authoritative_rule_outcome == "NON_CATALOG_SOFTWARE_REQUIRES_SECURITY_REVIEW"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_SECURITY_REVIEW"
    assert "TK-1044" in result.precedent_references[0]


# --- KB-05: Printer Troubleshooting ---
def test_kb05_initial_step_spooler_restart():
    result = policy_evaluator.evaluate_printer_issue(spooler_restarted=False)
    assert result.authoritative_rule_outcome == "INITIAL_PRINTER_TROUBLESHOOTING_STEP"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb05_issue_persists_missing_asset_tag():
    result = policy_evaluator.evaluate_printer_issue(spooler_restarted=True, issue_persists=True, printer_asset_tag=None)
    assert result.authoritative_rule_outcome == "MISSING_PRINTER_ASSET_TAG"
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP
    assert "printer_asset_tag" in result.missing_information


def test_kb05_issue_persists_with_asset_tag():
    result = policy_evaluator.evaluate_printer_issue(spooler_restarted=True, issue_persists=True, printer_asset_tag="PRN-FL3-009")
    assert result.authoritative_rule_outcome == "PRINTER_TICKET_LOGGED_WITH_ASSET_TAG"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "OPEN"
    assert "TK-1046" in result.precedent_references[0]


# --- KB-06: Email Mailbox Quota ---
def test_kb06_default_quota_25gb():
    result = policy_evaluator.evaluate_mailbox_quota(requested_quota_gb=25.0)
    assert result.authoritative_rule_outcome == "WITHIN_DEFAULT_QUOTA"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb06_increase_within_50gb_requires_manager_approval():
    result = policy_evaluator.evaluate_mailbox_quota(requested_quota_gb=35.0, manager_approval=False)
    assert result.authoritative_rule_outcome == "MANAGER_APPROVAL_REQUIRED_FOR_QUOTA_INCREASE"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_MANAGER_APPROVAL"


def test_kb06_increase_within_50gb_with_approval():
    result = policy_evaluator.evaluate_mailbox_quota(requested_quota_gb=35.0, manager_approval=True)
    assert result.authoritative_rule_outcome == "QUOTA_INCREASE_APPROVED"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_FULFILLMENT"
    assert "TK-1045" in result.precedent_references[0]


def test_kb06_increase_exceeding_50gb_cap_disallowed():
    result = policy_evaluator.evaluate_mailbox_quota(requested_quota_gb=55.0)
    assert result.authoritative_rule_outcome == "CANNOT_BE_INCREASED_UNDER_50GB_POLICY_CAP"
    assert result.workflow_action == WorkflowAction.RESOLVE


# --- KB-07: Guest Wi-Fi ---
def test_kb07_guest_wifi_self_service():
    result = policy_evaluator.evaluate_guest_wifi()
    assert result.authoritative_rule_outcome == "SELF_SERVICE_GUEST_WIFI_NO_TICKET_REQUIRED"
    assert result.workflow_action == WorkflowAction.RESOLVE
    assert "TK-1051" in result.precedent_references[0]


# --- KB-08: Expense Software Access ---
def test_kb08_access_provisioning_finance_owned():
    result = policy_evaluator.evaluate_expense_tool(request_type="grant_access")
    assert result.authoritative_rule_outcome == "ACCESS_GRANTED_BY_FINANCE_NOT_IT"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb08_technical_issue_existing_account():
    result = policy_evaluator.evaluate_expense_tool(request_type="technical_login", account_exists=True)
    assert result.authoritative_rule_outcome == "IT_ASSISTS_EXISTING_EXPENSE_ACCOUNT"
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP


# --- KB-09: Security Incident Reporting ---
def test_kb09_security_incident_mandatory_escalation():
    result = policy_evaluator.evaluate_security_incident(incident_type="phishing", forwarded_to_others=True)
    assert result.authoritative_rule_outcome == "MANDATORY_REPORT_TO_SECURITY_DO_NOT_FORWARD"
    assert result.workflow_action == WorkflowAction.ESCALATE
    assert result.operational_status == "ESCALATED_UNDER_INVESTIGATION"
    assert "TK-1048" in result.precedent_references[0]


# --- KB-10: Work-From-Home Equipment ---
def test_kb10_remote_days_boundary_3_days_ineligible():
    """Policy requires 'more than 3 days/week' (> 3.0). 3.0 days is strictly ineligible."""
    result = policy_evaluator.evaluate_wfh_equipment(remote_days_per_week=3.0, equipment_type="monitor")
    assert result.authoritative_rule_outcome == "INELIGIBLE_UNDER_REMOTE_WORK_THRESHOLD"
    assert result.workflow_action == WorkflowAction.RESOLVE


def test_kb10_remote_days_above_3_pending_approvals():
    result = policy_evaluator.evaluate_wfh_equipment(remote_days_per_week=4.0, equipment_type="monitor", manager_signoff=False)
    assert result.authoritative_rule_outcome == "PENDING_MANAGER_SIGNOFF_AND_FINANCE_PROCESSING"
    assert result.workflow_action == WorkflowAction.RESOLVE
    assert "TK-1047" in result.precedent_references[0]


def test_kb10_remote_days_above_3_approved():
    result = policy_evaluator.evaluate_wfh_equipment(remote_days_per_week=4.0, equipment_type="chair", manager_signoff=True, finance_processed=True)
    assert result.authoritative_rule_outcome == "APPROVED_FOR_EQUIPMENT_SHIPPING"
    assert result.workflow_action == WorkflowAction.CREATE_TICKET
    assert result.operational_status == "PENDING_SHIPPING"


def test_kb10_ineligible_equipment_type():
    result = policy_evaluator.evaluate_wfh_equipment(remote_days_per_week=4.0, equipment_type="standing_desk")
    assert result.authoritative_rule_outcome == "EQUIPMENT_OUTSIDE_ALLOWANCE_SCOPE"
    assert result.workflow_action == WorkflowAction.RESOLVE
