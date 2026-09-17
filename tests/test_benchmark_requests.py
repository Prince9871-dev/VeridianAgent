import json
import os
import pytest
from backend.app.policy.evaluator import policy_evaluator
from backend.app.policy.fallbacks import handle_unclear_input
from backend.app.models.common import WorkflowAction

BENCHMARK_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "derived", "benchmark_requests.json"
)


def load_benchmarks():
    with open(BENCHMARK_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("benchmarks", [])


@pytest.mark.parametrize("bm", load_benchmarks(), ids=lambda b: b["request_id"])
def test_benchmark_request_deterministic_outcome(bm):
    req_id = bm["request_id"]
    text = bm["request_text"]
    expected_action = getattr(WorkflowAction, bm["expected_workflow_action"])

    if req_id == "REQ-01":
        # Aditi Sharma: Dead laptop, ~3.5 years old
        result = policy_evaluator.evaluate_laptop_replacement(service_age_years=3.5, hardware_failure_verified=True, lead_time_days=14)
        assert result.workflow_action == expected_action
        assert "KB-03" in result.matched_policy_ids
        assert "POL-ASSET-01" in result.matched_policy_ids
        assert "Finance sign-off" in result.authoritative_approvals

    elif req_id == "REQ-02":
        # Vikram Chawla: Guest Wi-Fi access tomorrow
        result = policy_evaluator.evaluate_guest_wifi()
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-07"

    elif req_id == "REQ-03":
        # Karan Mehta: Locked out after 6 attempts
        result = policy_evaluator.evaluate_password_reset(is_locked_out=True, failed_attempts=6)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-01"

    elif req_id == "REQ-04":
        # Ritu Bhatia: Non-catalog software tool
        result = policy_evaluator.evaluate_software_request(software_name="Data Analysis Tool", in_approved_catalog=False)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-04"
        assert result.operational_status == "PENDING_SECURITY_REVIEW"

    elif req_id == "REQ-05":
        # Sanjay Oberoi: VPN expired
        result = policy_evaluator.evaluate_vpn_access(employment_type="full_time")
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-02"

    elif req_id == "REQ-06":
        # Meera Iyer: Printer paper jam on 3rd floor (spooler guidance & missing asset tag follow-up)
        result = policy_evaluator.evaluate_printer_issue(spooler_restarted=False, issue_persists=True, printer_asset_tag=None)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-05"

    elif req_id == "REQ-07":
        # Farhan Ali: WFH 4 days/week, requesting monitor
        result = policy_evaluator.evaluate_wfh_equipment(remote_days_per_week=4.0, equipment_type="monitor", manager_signoff=False)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-10"
        assert "Finance processing" in result.authoritative_approvals

    elif req_id == "REQ-08":
        # Ananya Reddy: Phishing email forwarded to teammates
        result = policy_evaluator.evaluate_security_incident(incident_type="phishing", forwarded_to_others=True)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-09"

    elif req_id == "REQ-09":
        # Rohit Desai: Mailbox full, cannot send email
        result = policy_evaluator.evaluate_mailbox_quota(requested_quota_gb=25.0)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-06"

    elif req_id == "REQ-10":
        # Kavya Pillai: Admin access to finance reporting server
        result = policy_evaluator.evaluate_admin_access(requested_system="finance reporting server")
        assert result.workflow_action == expected_action
        assert "TK-1050" in result.precedent_references[0]

    elif req_id == "REQ-11":
        # Nikhil Bansal: New contractor VPN
        result = policy_evaluator.evaluate_vpn_access(employment_type="contractor", manager_approval_submitted=False)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-02"

    elif req_id == "REQ-12":
        # Sneha Kulkarni: Expense tool invalid credentials (account exists)
        result = policy_evaluator.evaluate_expense_tool(request_type="technical_login", account_exists=True)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-08"

    elif req_id == "REQ-13":
        # Aman Gupta: Screen flickering on 2 yr old laptop, wants fix not replacement
        result = policy_evaluator.evaluate_laptop_replacement(service_age_years=2.0, hardware_failure_verified=False)
        # Ineligible for full replacement under KB-03, direct to repair
        assert result.authoritative_rule_outcome == "INELIGIBLE_UNDER_KB03"

    elif req_id == "REQ-14":
        # Tanya Chopra: Browser extension for productivity
        result = policy_evaluator.evaluate_software_request(software_name="Productivity Tracking Extension", in_approved_catalog=False)
        assert result.workflow_action == expected_action
        assert result.matched_policy_id == "KB-04"

    elif req_id == "REQ-15":
        # Rahul Menon: "hey can you help, its not working"
        result = handle_unclear_input(text)
        assert result.workflow_action == expected_action
        assert result.is_engineering_fallback is True
        assert result.matched_policy_id is None
