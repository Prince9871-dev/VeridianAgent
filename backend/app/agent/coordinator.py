import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from backend.app.models.common import (
    AuditEventType,
    TicketSeverity,
    WorkflowAction,
)
from backend.app.models.ticket import TicketCreate, Ticket
from backend.app.models.request import (
    EmployeeMessage,
    IntentAnalysis,
    PolicyEvaluationResult,
    ServiceAgentResponse,
)
from backend.app.policy.schema import (
    DeterministicEvaluationResult,
    SourceExplicitness,
)
from backend.app.policy.catalog import policy_catalog
from backend.app.policy.evaluator import policy_evaluator
from backend.app.policy.fallbacks import (
    handle_no_applicable_policy,
    handle_unclear_input,
)
from backend.app.tickets.manager import ticket_manager
from backend.app.audit.logger import audit_logger
from backend.app.agent.session import session_store, SessionState
from backend.app.agent.factory import get_llm_provider
from backend.app.agent.providers.gemini import ProviderUnavailableError

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Central Agent Coordinator linking:
    1. LLM NLU Fact Extraction (Non-Authoritative)
    2. Multi-turn Session State & Fact Accumulation
    3. Deterministic Policy Engine (Sole Authority)
    4. Structured Ticket Lifecycle Manager
    5. Append-Only Audit Logger
    """

    async def process_message(self, request: EmployeeMessage) -> ServiceAgentResponse:
        session_id = request.session_id
        employee_id = request.employee_id
        content = request.content.strip()

        # Step 1: Ingest & Audit Event (REQUEST_RECEIVED)
        audit_logger.log_event(
            event_type=AuditEventType.REQUEST_RECEIVED,
            actor="USER",
            session_id=session_id,
            employee_id=employee_id,
            action_taken="INGEST",
            details={"content": content, "metadata": request.metadata},
        )

        # Step 2: Session Retrieval & History Recording
        session = session_store.get_or_create(session_id=session_id, employee_id=employee_id)
        session.add_message(role="employee", content=content)

        # Step 3: LLM Natural Language Understanding & Fact Extraction
        provider = get_llm_provider()
        intent_analysis: IntentAnalysis
        try:
            intent_analysis = await provider.extract_structured_data(
                prompt=content,
                schema=IntentAnalysis,
            )
        except ProviderUnavailableError as e:
            logger.warning(f"LLM provider unavailable, falling back to mock provider: {e}")
            from backend.app.agent.providers.mock import MockLLMProvider
            fallback_provider = MockLLMProvider()
            intent_analysis = await fallback_provider.extract_structured_data(
                prompt=content,
                schema=IntentAnalysis,
            )
        except Exception as e:
            logger.error(f"Unexpected error in LLM extraction: {e}")
            intent_analysis = IntentAnalysis(
                raw_intent="EXTRACTION_FAILURE",
                extracted_facts={},
                missing_fields=[],
                candidate_policy_id=None,
                confidence=0.0,
            )

        audit_logger.log_event(
            event_type=AuditEventType.INTENT_CLASSIFIED,
            actor="AGENT",
            session_id=session_id,
            employee_id=employee_id,
            action_taken="CLASSIFY",
            details={
                "raw_intent": intent_analysis.raw_intent,
                "extracted_facts": intent_analysis.extracted_facts,
                "candidate_policy_id": intent_analysis.candidate_policy_id,
            },
        )

        # Step 4: Multi-Turn Fact Accumulation (Constraint 4: safe additive merge)
        session.merge_facts(intent_analysis.extracted_facts)
        accumulated_facts = session.accumulated_facts

        # Step 5: Policy Routing Validation (Constraint 2: candidate_policy_id is ONLY a routing hint)
        validated_policy_id = self._resolve_and_validate_policy_id(
            candidate_id=intent_analysis.candidate_policy_id,
            active_session_policy=session.active_policy_id,
            facts=accumulated_facts,
            raw_text=content,
        )

        if validated_policy_id:
            session.active_policy_id = validated_policy_id

        # Step 6: Deterministic Policy Evaluation (Sole Authority)
        eval_result = self._dispatch_to_policy_engine(
            policy_id=validated_policy_id,
            facts=accumulated_facts,
            raw_text=content,
        )

        audit_logger.log_event(
            event_type=AuditEventType.POLICY_EVALUATED,
            actor="POLICY_ENGINE",
            session_id=session_id,
            employee_id=employee_id,
            action_taken=eval_result.workflow_action.value,
            policy_id=eval_result.matched_policy_id,
            policy_citation=eval_result.authoritative_citations[0] if eval_result.authoritative_citations else None,
            details={
                "outcome": eval_result.authoritative_rule_outcome,
                "workflow_action": eval_result.workflow_action.value,
                "operational_status": eval_result.operational_status,
                "required_approvals": eval_result.authoritative_approvals,
                "is_fallback": eval_result.is_engineering_fallback,
            },
        )

        # Step 7: Workflow Execution & State Management
        created_ticket: Optional[Ticket] = None
        follow_up_question: Optional[str] = None
        action = eval_result.workflow_action

        if action == WorkflowAction.ASK_FOLLOW_UP:
            session.pending_missing_fields = eval_result.missing_information
            follow_up_question = eval_result.user_message
            audit_logger.log_event(
                event_type=AuditEventType.FOLLOW_UP_REQUESTED,
                actor="AGENT",
                session_id=session_id,
                employee_id=employee_id,
                action_taken="ASK_FOLLOW_UP",
                policy_id=eval_result.matched_policy_id,
                details={"missing_fields": eval_result.missing_information, "question": follow_up_question},
            )

        elif action == WorkflowAction.RESOLVE:
            session.is_concluded = True
            audit_logger.log_event(
                event_type=AuditEventType.REQUEST_RESOLVED,
                actor="POLICY_ENGINE",
                session_id=session_id,
                employee_id=employee_id,
                action_taken="RESOLVE",
                policy_id=eval_result.matched_policy_id,
                details={"outcome": eval_result.authoritative_rule_outcome},
            )

        elif action in [WorkflowAction.CREATE_TICKET, WorkflowAction.ESCALATE]:
            # Constraint 8: Reuse existing TicketManager
            severity = TicketSeverity.HIGH if action == WorkflowAction.ESCALATE else TicketSeverity.MEDIUM
            ticket_data = TicketCreate(
                employee_id=employee_id,
                employee_name=request.metadata.get("employee_name", "Employee"),
                category=self._determine_ticket_category(eval_result.matched_policy_id),
                title=self._generate_ticket_title(eval_result, content),
                description=f"Request: {content}\nAuthoritative Rule Outcome: {eval_result.authoritative_rule_outcome}\nRequired Approvals: {', '.join(eval_result.authoritative_approvals) or 'None'}",
                severity=severity,
                policy_id=eval_result.matched_policy_id,
                policy_citation=eval_result.authoritative_citations[0] if eval_result.authoritative_citations else None,
                tags=[eval_result.matched_policy_id or "GENERAL", eval_result.operational_queue or "IT"],
            )
            created_ticket = await ticket_manager.create_ticket(ticket_data)

            if eval_result.operational_status:
                from backend.app.models.common import TicketStatus
                status_map = {
                    "PENDING_APPROVAL": TicketStatus.OPEN,
                    "PENDING_SECURITY_REVIEW": TicketStatus.OPEN,
                    "PENDING_MANAGER_APPROVAL": TicketStatus.OPEN,
                    "PENDING_FULFILLMENT": TicketStatus.OPEN,
                    "ESCALATED_UNDER_INVESTIGATION": TicketStatus.ESCALATED,
                    "OPEN": TicketStatus.OPEN,
                }
                if eval_result.operational_status in status_map:
                    await ticket_manager.update_status(
                        ticket_id=created_ticket.id,
                        status=status_map[eval_result.operational_status],
                        notes=f"Queue: {eval_result.operational_queue}",
                        escalation_reason=eval_result.authoritative_rule_outcome if action == WorkflowAction.ESCALATE else None,
                    )

            if action == WorkflowAction.ESCALATE:
                audit_logger.log_event(
                    event_type=AuditEventType.REQUEST_ESCALATED,
                    actor="POLICY_ENGINE",
                    session_id=session_id,
                    employee_id=employee_id,
                    action_taken="ESCALATE",
                    policy_id=eval_result.matched_policy_id,
                    details={"ticket_id": created_ticket.id, "reason": eval_result.authoritative_rule_outcome},
                )

            audit_logger.log_event(
                event_type=AuditEventType.TICKET_CREATED,
                actor="SYSTEM",
                session_id=session_id,
                employee_id=employee_id,
                action_taken="CREATE_TICKET",
                policy_id=eval_result.matched_policy_id,
                details={"ticket_id": created_ticket.id, "severity": severity.value, "queue": eval_result.operational_queue},
            )

        # Step 8: Assemble Coordinated Response
        agent_message = eval_result.user_message
        if created_ticket:
            agent_message += f"\n\nA service ticket ({created_ticket.id}) has been created and assigned to {eval_result.operational_queue or 'IT Support'}."

        session.add_message(
            role="agent",
            content=agent_message,
            metadata={"action": action.value, "ticket_id": created_ticket.id if created_ticket else None},
        )
        session_store.save(session)

        citation_str = " & ".join(eval_result.authoritative_citations) if eval_result.authoritative_citations else None

        return ServiceAgentResponse(
            session_id=session_id,
            message=agent_message,
            action=action,
            intent_analysis=intent_analysis,
            policy_evaluation=PolicyEvaluationResult(
                policy_id=eval_result.matched_policy_id,
                policy_name=policy_catalog.get_policy(eval_result.matched_policy_id).title if eval_result.matched_policy_id and policy_catalog.get_policy(eval_result.matched_policy_id) else None,
                clause_cited=eval_result.authoritative_source_text,
                is_permitted="PERMITTED" in eval_result.authoritative_rule_outcome or "APPROVED" in eval_result.authoritative_rule_outcome or "ELIGIBLE" in eval_result.authoritative_rule_outcome,
                requires_approval=len(eval_result.authoritative_approvals) > 0,
                escalation_required=action == WorkflowAction.ESCALATE,
                escalation_reason=eval_result.authoritative_rule_outcome if action == WorkflowAction.ESCALATE else None,
            ),
            deterministic_evaluation=eval_result.model_dump(),
            follow_up_question=follow_up_question,
            ticket=created_ticket,
            source_citation=citation_str,
            audit_event_id=f"AUD-{session_id[-6:]}",
            timestamp=datetime.now(timezone.utc),
        )

    def _resolve_and_validate_policy_id(
        self,
        candidate_id: Optional[str],
        active_session_policy: Optional[str],
        facts: Dict[str, Any],
        raw_text: str,
    ) -> Optional[str]:
        """
        Validates candidate_policy_id against the catalog and facts (Constraint 2).
        Candidate is strictly a non-authoritative routing hint.
        """
        lower = raw_text.lower()

        # If a candidate ID was provided, verify it exists in catalog AND is relevant
        if candidate_id:
            policy_record = policy_catalog.get_policy(candidate_id)
            if policy_record is not None:
                if self._is_candidate_relevant(candidate_id, facts, lower):
                    return candidate_id
                else:
                    logger.warning(
                        f"Candidate policy ID '{candidate_id}' rejected as irrelevant to extracted facts/content."
                    )
            else:
                logger.warning(
                    f"Candidate policy ID '{candidate_id}' rejected: does not exist in authoritative catalog."
                )

        # If previous turn had an active policy and user is answering a follow-up
        if active_session_policy and policy_catalog.get_policy(active_session_policy):
            return active_session_policy

        # Fallback to grounded semantic heuristics across facts
        if "printer_asset_tag" in facts or "spooler_restarted" in facts or "printer" in lower:
            return "KB-05"
        if "service_age_years" in facts or "hardware_failure_verified" in facts or "laptop" in lower:
            return "KB-03"
        if "employment_type" in facts or "vpn" in lower:
            return "KB-02"
        if "is_locked_out" in facts or "password" in lower:
            return "KB-01"
        if "software_name" in facts or "in_approved_catalog" in facts:
            return "KB-04"
        if "requested_quota_gb" in facts or "mailbox" in lower:
            return "KB-06"
        if "guest" in lower and "wi-fi" in lower:
            return "KB-07"
        if "expense" in lower:
            return "KB-08"
        if "phishing" in lower or "malware" in lower:
            return "KB-09"
        if "remote_days_per_week" in facts or "working from home" in lower or "wfh" in lower:
            return "KB-10"

        return None

    def _is_candidate_relevant(self, candidate_id: str, facts: Dict[str, Any], text_lower: str) -> bool:
        """Confirm that candidate policy ID is plausibly relevant to current facts or text."""
        relevant_keywords = {
            "KB-01": ["password", "locked", "unlock", "login", "failed_attempts", "is_locked_out"],
            "KB-02": ["vpn", "contractor", "remote access", "credentials", "employment_type"],
            "KB-03": ["laptop", "hardware", "device", "replacement", "service_age_years", "refresh"],
            "POL-ASSET-01": ["laptop", "hardware", "device", "replacement", "service_age_years", "refresh", "asset"],
            "KB-04": ["software", "install", "application", "license", "in_approved_catalog", "software_name"],
            "KB-05": ["printer", "print", "spooler", "paper", "printer_asset_tag"],
            "KB-06": ["mailbox", "quota", "email", "storage", "requested_quota_gb", "inbox"],
            "KB-07": ["wifi", "wi-fi", "guest", "visitor", "network"],
            "KB-08": ["expense", "concur", "reimbursement", "finance", "expense_tool"],
            "KB-09": ["phishing", "malware", "virus", "suspicious", "security", "incident_type", "hacked"],
            "KB-10": ["wfh", "remote", "working from home", "home office", "monitor", "chair", "remote_days_per_week"],
            "POL-ADMIN-01": ["admin", "administrator", "root", "privileged", "sudo", "is_admin_access_request"],
        }
        keywords = relevant_keywords.get(candidate_id, [])
        if any(kw in text_lower for kw in keywords):
            return True
        if any(kw in facts for kw in keywords):
            return True
        return False

    def _dispatch_to_policy_engine(
        self,
        policy_id: Optional[str],
        facts: Dict[str, Any],
        raw_text: str,
    ) -> DeterministicEvaluationResult:
        """Dispatches accumulated facts to the deterministic evaluator."""
        lower = raw_text.lower()

        if policy_id == "KB-01":
            return policy_evaluator.evaluate_password_reset(
                is_locked_out=facts.get("is_locked_out", False),
                failed_attempts=facts.get("failed_attempts"),
            )
        elif policy_id == "KB-02":
            return policy_evaluator.evaluate_vpn_access(
                employment_type=facts.get("employment_type", "full_time"),
                manager_approval_submitted=facts.get("manager_approval_submitted", False),
                credential_age_days=facts.get("credential_age_days"),
            )
        elif policy_id in ["KB-03", "POL-ASSET-01"]:
            return policy_evaluator.evaluate_laptop_replacement(
                service_age_years=float(facts.get("service_age_years", 0.0)),
                hardware_failure_verified=facts.get("hardware_failure_verified", False),
                lead_time_days=facts.get("lead_time_days", 14),
            )
        elif policy_id == "KB-04":
            return policy_evaluator.evaluate_software_request(
                software_name=facts.get("software_name", "Unknown Software"),
                in_approved_catalog=facts.get("in_approved_catalog", False),
            )
        elif policy_id == "KB-05":
            return policy_evaluator.evaluate_printer_issue(
                spooler_restarted=facts.get("spooler_restarted", False),
                issue_persists=facts.get("issue_persists", True),
                printer_asset_tag=facts.get("printer_asset_tag"),
            )
        elif policy_id == "KB-06":
            return policy_evaluator.evaluate_mailbox_quota(
                requested_quota_gb=float(facts.get("requested_quota_gb", 25.0)),
                manager_approval=facts.get("manager_approval", False),
            )
        elif policy_id == "KB-07":
            return policy_evaluator.evaluate_guest_wifi()
        elif policy_id == "KB-08":
            return policy_evaluator.evaluate_expense_tool(
                request_type=facts.get("request_type", "technical_login"),
                account_exists=facts.get("account_exists", False),
            )
        elif policy_id == "KB-09":
            return policy_evaluator.evaluate_security_incident(
                incident_type=facts.get("incident_type", "phishing"),
                reported_content=facts.get("reported_content", raw_text),
                forwarded_to_others=facts.get("forwarded_to_others", False),
            )
        elif policy_id == "KB-10":
            return policy_evaluator.evaluate_wfh_equipment(
                remote_days_per_week=float(facts.get("remote_days_per_week", 0.0)),
                equipment_type=facts.get("equipment_type", "monitor"),
                manager_signoff=facts.get("manager_signoff", False),
                finance_processed=facts.get("finance_processed", False),
            )
        elif "admin" in lower or facts.get("is_admin_access_request", False):
            return policy_evaluator.evaluate_admin_access(
                requested_system=facts.get("requested_system", "server"),
                business_justification=facts.get("business_justification"),
            )
        elif len(lower.split()) < 7 and ("help" in lower or "working" in lower):
            return handle_unclear_input(raw_text)
        else:
            return handle_no_applicable_policy(raw_text)

    def _determine_ticket_category(self, policy_id: Optional[str]) -> str:
        if not policy_id:
            return "General IT Service"
        policy = policy_catalog.get_policy(policy_id)
        return policy.category if policy else "General IT Support"

    def _generate_ticket_title(self, eval_result: DeterministicEvaluationResult, raw_content: str) -> str:
        if eval_result.matched_policy_id:
            policy = policy_catalog.get_policy(eval_result.matched_policy_id)
            if policy:
                return f"{policy.title} Request"
        snippet = raw_content[:45].strip()
        return f"IT Support: {snippet}..."


# Global singleton instance
agent_coordinator = AgentCoordinator()
