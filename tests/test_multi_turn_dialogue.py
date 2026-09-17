import pytest
from backend.app.agent.coordinator import AgentCoordinator
from backend.app.agent.session import session_store
from backend.app.models.request import EmployeeMessage
from backend.app.models.common import WorkflowAction


@pytest.fixture
def coordinator():
    return AgentCoordinator()


@pytest.mark.asyncio
async def test_multi_turn_printer_troubleshooting_flow(coordinator):
    """
    Multi-turn test: Printer issue.
    Turn 1: User reports jammed printer without asset tag -> ASK_FOLLOW_UP
    Turn 2: User provides asset tag and confirms spooler restart -> CREATE_TICKET
    """
    session_id = "test-session-multi-printer-01"
    session_store.reset(session_id)

    # Turn 1: Incomplete request - spooler restarted but asset tag missing
    turn1_req = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-2001",
        content="I restarted the print spooler, but the 3rd floor printer is still not working.",
    )
    turn1_res = await coordinator.process_message(turn1_req)

    assert turn1_res.action == WorkflowAction.ASK_FOLLOW_UP
    assert turn1_res.follow_up_question is not None
    assert "asset tag" in turn1_res.follow_up_question.lower()
    assert turn1_res.ticket is None

    # Check session state
    session = session_store.get(session_id)
    assert session is not None
    assert len(session.history) == 2  # 1 employee + 1 agent

    # Turn 2: Providing the missing information
    turn2_req = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-2001",
        content="The asset tag is PRN-3FL-02.",
    )
    turn2_res = await coordinator.process_message(turn2_req)

    assert turn2_res.action == WorkflowAction.CREATE_TICKET
    assert turn2_res.ticket is not None
    assert turn2_res.ticket.policy_id == "KB-05"
    assert "PRN-3FL-02" in turn2_res.ticket.title or "PRN-3FL-02" in turn2_res.ticket.description

    # Verify history is chronological
    session = session_store.get(session_id)
    assert len(session.history) == 4
    roles = [m.role for m in session.history]
    assert roles == ["employee", "agent", "employee", "agent"]


@pytest.mark.asyncio
async def test_multi_turn_contractor_vpn_flow(coordinator):
    """
    Multi-turn test: Contractor VPN access.
    Turn 1: Contractor asks for VPN -> ASK_FOLLOW_UP for manager approval form confirmation
    Turn 2: Confirms form was submitted -> CREATE_TICKET (pending manager/sponsor approval)
    """
    session_id = "test-session-multi-vpn-02"
    session_store.reset(session_id)

    # Turn 1
    req1 = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-CONT-10",
        content="I am an external contractor and need VPN access to the corporate network.",
    )
    res1 = await coordinator.process_message(req1)
    assert res1.action == WorkflowAction.ASK_FOLLOW_UP
    assert "form" in res1.message.lower() or "approval" in res1.message.lower()

    # Turn 2
    req2 = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-CONT-10",
        content="Yes, my manager has already submitted the approved contractor access form.",
    )
    res2 = await coordinator.process_message(req2)
    assert res2.action == WorkflowAction.CREATE_TICKET
    assert res2.ticket is not None
    assert res2.ticket.policy_id == "KB-02"


@pytest.mark.asyncio
async def test_multi_turn_fact_preservation_and_conflict_resolution(coordinator):
    """
    Constraint 4 & 12:
    1. Facts must accumulate additively without deleting previously established fields.
    2. If a user corrects a prior fact (conflicting facts), the new value updates cleanly.
    """
    session_id = "test-session-fact-merge-03"
    session_store.reset(session_id)

    # Turn 1: User asks for a monitor, works 2 days remotely (ineligible < 3 days)
    req1 = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-3001",
        content="I am working from home 2 days a week and would like an external monitor.",
    )
    res1 = await coordinator.process_message(req1)
    assert res1.action == WorkflowAction.RESOLVE
    assert res1.deterministic_evaluation["authoritative_rule_outcome"] == "INELIGIBLE_UNDER_REMOTE_WORK_THRESHOLD"
    assert "more than 3 days" in res1.message.lower()

    session = session_store.get(session_id)
    assert session.accumulated_facts.get("remote_days_per_week") == 2.0
    assert session.accumulated_facts.get("equipment_type") == "monitor"

    # Turn 2: User corrects remote days to 4 days, and notes approvals
    req2 = EmployeeMessage(
        session_id=session_id,
        employee_id="EMP-3001",
        content="Actually, my remote schedule was updated to 4 days a week. My manager signed off and Finance processed it yesterday.",
    )
    res2 = await coordinator.process_message(req2)

    # Re-evaluates with updated fact: 4 days is eligible!
    session = session_store.get(session_id)
    assert session.accumulated_facts.get("remote_days_per_week") == 4.0
    # Fact from Turn 1 (equipment_type="monitor") was NOT lost
    assert session.accumulated_facts.get("equipment_type") == "monitor"

    # Now creates ticket pending manager & finance approvals
    assert res2.action == WorkflowAction.CREATE_TICKET
    assert res2.ticket is not None
    assert res2.ticket.policy_id == "KB-10"


@pytest.mark.asyncio
async def test_session_reset_clears_state(coordinator):
    """Verify that resetting a session cleanly clears facts and history."""
    session_id = "test-session-reset-04"
    session = session_store.get_or_create(session_id, "EMP-4001")
    session.add_message("employee", "Hello")
    session.merge_facts({"test_fact": "value123"})
    session_store.save(session)

    assert session_store.get(session_id) is not None
    assert "test_fact" in session_store.get(session_id).accumulated_facts

    session_store.reset(session_id)
    assert session_store.get(session_id) is None
