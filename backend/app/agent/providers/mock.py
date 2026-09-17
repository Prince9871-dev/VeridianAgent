import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.app.agent.base import BaseLLMProvider, LLMCompletionResponse, LLMMessage
from backend.app.models.request import IntentAnalysis


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, offline mock LLM provider.
    
    Adheres strictly to Governance Constraint 3:
    Parses natural language employee requests and extracts structured facts & intent.
    DOES NOT make policy determinations or hardcode workflow actions (RESOLVE, CREATE_TICKET).
    The extracted facts are fed to the Policy Engine which alone determines the outcome.
    """

    def __init__(self, default_response: str = "Mock agent conversational formulation."):
        self.default_response = default_response

    async def generate_response(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMCompletionResponse:
        last_msg = messages[-1].content if messages else ""
        return LLMCompletionResponse(
            content=f"Under Veridian IT policies, your request regarding '{last_msg[:40]}...' is being evaluated.",
            provider="mock",
            model="mock-v1",
            usage={"prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35},
        )

    async def extract_structured_data(
        self,
        prompt: str,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """
        Extracts structured intent and parameters from natural language prompts.
        Matches semantic patterns from employee inquiries to extract raw facts.
        """
        lower = prompt.lower()
        facts: Dict[str, Any] = {}
        intent = "GENERAL_INQUIRY"
        candidate_policy_id: Optional[str] = None

        # 1. Password Lockout / Reset (e.g. REQ-03)
        if "locked out" in lower or "password" in lower:
            intent = "PASSWORD_LOCKOUT_RESET_INQUIRY"
            candidate_policy_id = "KB-01"
            attempts_match = re.search(r"(\d+)\s*(?:times|attempts)", lower)
            if attempts_match:
                attempts = int(attempts_match.group(1))
                facts["failed_attempts"] = attempts
                facts["is_locked_out"] = attempts >= 5 or "locked out" in lower
            else:
                facts["is_locked_out"] = "locked out" in lower

        # 2. Guest Wi-Fi (e.g. REQ-02)
        elif "guest" in lower and ("wi-fi" in lower or "wifi" in lower or "access" in lower):
            intent = "GUEST_WIFI_REQUEST"
            candidate_policy_id = "KB-07"

        # 3. Software Installation / Extensions (e.g. REQ-04, REQ-14)
        elif "install" in lower or "software" in lower or "extension" in lower:
            intent = "SOFTWARE_INSTALLATION_REQUEST"
            candidate_policy_id = "KB-04"
            if "browser extension" in lower or "productivity" in lower:
                facts["software_name"] = "Productivity Tracking Extension"
                facts["in_approved_catalog"] = False
            elif "data-analysis" in lower or "data analysis" in lower:
                facts["software_name"] = "Data Analysis Tool"
                facts["in_approved_catalog"] = False
            elif "approved" in lower or "catalog" in lower:
                facts["software_name"] = "Catalog Tool"
                facts["in_approved_catalog"] = True
            else:
                facts["software_name"] = "Requested Software"
                facts["in_approved_catalog"] = False

        # 4. Laptop / Hardware Replacement Inquiry (e.g. REQ-01, REQ-13)
        elif "laptop" in lower or "macbook" in lower:
            if "turn on" in lower or "dead" in lower or "completely dead" in lower:
                intent = "LAPTOP_FAILURE_REPLACEMENT_INQUIRY"
                candidate_policy_id = "KB-03"
                facts["asset_type"] = "laptop"
                facts["hardware_failure_verified"] = True
                facts["lead_time_days"] = 14
                # Extract years if present (e.g. "3.5 years")
                years_match = re.search(r"(\d+(?:\.\d+)?)\s*years?", lower)
                if years_match:
                    facts["service_age_years"] = float(years_match.group(1))
                else:
                    facts["service_age_years"] = 3.5
            elif "flickering" in lower or "fix" in lower:
                intent = "LAPTOP_SCREEN_REPAIR_INQUIRY"
                candidate_policy_id = "KB-03"
                facts["asset_type"] = "laptop"
                facts["hardware_failure_verified"] = False
                facts["is_repair_request"] = True
                years_match = re.search(r"(\d+(?:\.\d+)?)\s*years?", lower)
                facts["service_age_years"] = float(years_match.group(1)) if years_match else 2.0
            else:
                intent = "LAPTOP_GENERAL_INQUIRY"
                candidate_policy_id = "KB-03"
                facts["asset_type"] = "laptop"

        # 5. VPN Access & Credentials (e.g. REQ-05, REQ-11)
        elif "vpn" in lower or "contractor access" in lower or "access form" in lower:
            intent = "VPN_ACCESS_INQUIRY"
            candidate_policy_id = "KB-02"
            if "contractor" in lower:
                facts["employment_type"] = "contractor"
            elif "full_time" in lower or "full-time" in lower:
                facts["employment_type"] = "full_time"
            if "approved" in lower or "submitted" in lower:
                facts["manager_approval_submitted"] = True
            if "expired" in lower:
                facts["credential_expired"] = True

        # 6. Printer Troubleshooting & Asset Tag (e.g. REQ-06)
        elif "printer" in lower or "spooler" in lower or "paper jam" in lower or "asset tag" in lower or "prn-" in lower:
            intent = "PRINTER_TROUBLESHOOTING_INQUIRY"
            candidate_policy_id = "KB-05"
            facts["issue_persists"] = True
            if "restarted" in lower or "checked" in lower:
                facts["spooler_restarted"] = True
            tag_match = re.search(r"(?:asset\s*tag\s*(?:is|:)?\s*([A-Z0-9\-]+))", prompt, re.IGNORECASE)
            if tag_match:
                facts["printer_asset_tag"] = tag_match.group(1).strip()
            elif "prn-" in lower:
                tag_word = [w for w in prompt.split() if "prn-" in w.lower()]
                if tag_word:
                    facts["printer_asset_tag"] = tag_word[0].strip(".,")

        # 7. Work-From-Home / Remote Equipment (e.g. REQ-07)
        elif "working from home" in lower or "wfh" in lower or "remote" in lower:
            intent = "REMOTE_WORK_EQUIPMENT_INQUIRY"
            candidate_policy_id = "KB-10"
            days_match = re.search(r"(\d+(?:\.\d+)?)\s*days?", lower)
            if days_match:
                facts["remote_days_per_week"] = float(days_match.group(1))
            else:
                facts["remote_days_per_week"] = 4.0 if "4 days" in lower else 0.0

            if "monitor" in lower:
                facts["equipment_type"] = "monitor"
            elif "chair" in lower:
                facts["equipment_type"] = "chair"
            else:
                facts["equipment_type"] = "monitor"

            facts["manager_signoff"] = "signed" in lower or "approved" in lower
            facts["finance_processed"] = "finance processed" in lower or "processed" in lower

        # 8. Security Incident / Phishing (e.g. REQ-08)
        elif "phishing" in lower or "malware" in lower or "unauthorized access" in lower:
            intent = "SECURITY_INCIDENT_REPORT"
            candidate_policy_id = "KB-09"
            facts["incident_type"] = "phishing" if "phishing" in lower else "malware"
            facts["forwarded_to_others"] = "forwarding" in lower or "forwarded" in lower or "teammates" in lower
            facts["reported_content"] = prompt

        # 9. Email Mailbox Quota (e.g. REQ-09)
        elif "mailbox" in lower or "quota" in lower:
            intent = "MAILBOX_QUOTA_INQUIRY"
            candidate_policy_id = "KB-06"
            facts["requested_quota_gb"] = 25.0
            quota_match = re.search(r"(\d+)\s*gb", lower)
            if quota_match:
                facts["requested_quota_gb"] = float(quota_match.group(1))
            facts["manager_approval"] = "manager approved" in lower or "approved" in lower

        # 10. Admin Access to Servers (e.g. REQ-10)
        elif "admin access" in lower or "admin rights" in lower:
            intent = "ADMIN_ACCESS_REQUEST"
            candidate_policy_id = None  # No authoritative KB policy grants admin rights
            facts["is_admin_access_request"] = True
            facts["requested_system"] = "finance reporting server" if "finance" in lower else "server"

        # 11. Expense Management Tool (e.g. REQ-12)
        elif "expense" in lower:
            intent = "EXPENSE_TOOL_INQUIRY"
            candidate_policy_id = "KB-08"
            facts["request_type"] = "grant_access" if ("access" in lower or "new" in lower) else "technical_login"
            facts["account_exists"] = "can't log into" in lower or "credentials" in lower or "exists" in lower

        # 12. Vague / Incomplete (e.g. REQ-15)
        elif ("not working" in lower or "help" in lower) and len(lower.split()) <= 10:
            intent = "UNCLEAR_INQUIRY"
            candidate_policy_id = None
            facts["is_unclear_inquiry"] = True

        # Build and validate through Pydantic schema
        return schema(
            raw_intent=intent,
            extracted_facts=facts,
            missing_fields=[],
            candidate_policy_id=candidate_policy_id,
            confidence=0.98,
        )
