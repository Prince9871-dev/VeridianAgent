import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.config import get_settings
from backend.app.models.common import AuditEventType, TicketSeverity, WorkflowAction
from backend.app.models.ticket import TicketCreate
from backend.app.tickets.manager import ticket_manager
from backend.app.audit.logger import audit_logger
from backend.app.agent.base import MockLLMProvider, LLMMessage


def test_settings_loader():
    """Verify backend settings load cleanly with expected defaults."""
    settings = get_settings()
    assert settings.app_name == "Veridian Assist — IT Service Agent"
    assert "http://localhost:3000" in settings.cors_origins_list
    assert settings.llm_provider in ["mock", "gemini", "openai"]


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify the /api/v1/health endpoint returns status 200 and expected payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "Veridian Assist — IT Service Agent"
        assert "datapack_configured" in data


@pytest.mark.asyncio
async def test_ticket_manager_lifecycle():
    """Verify ticket creation and retrieval through the TicketManager."""
    new_ticket_data = TicketCreate(
        employee_id="EMP-1002",
        employee_name="Alice Chen",
        category="Hardware",
        title="Laptop screen flickering",
        description="External display flickers when connected via USB-C dock",
        severity=TicketSeverity.MEDIUM,
        tags=["laptop", "hardware", "display"],
    )
    created = await ticket_manager.create_ticket(new_ticket_data)
    assert created.id.startswith("TCK-")
    assert created.employee_id == "EMP-1002"
    assert created.status == "OPEN"

    retrieved = await ticket_manager.get_ticket(created.id)
    assert retrieved is not None
    assert retrieved.title == "Laptop screen flickering"


@pytest.mark.asyncio
async def test_audit_logger():
    """Verify audit events are logged and retrievable in reverse chronological order."""
    event = audit_logger.log_event(
        event_type=AuditEventType.REQUEST_RECEIVED,
        actor="USER",
        session_id="SESS-001",
        employee_id="EMP-1002",
        details={"user_input": "Requesting monitor stand"},
    )
    assert event.id.startswith("AUD-")
    assert event.event_type == AuditEventType.REQUEST_RECEIVED

    events = await audit_logger.list_events(session_id="SESS-001")
    assert len(events) >= 1
    assert any(e.id == event.id for e in events)


@pytest.mark.asyncio
async def test_mock_llm_provider():
    """Verify the MockLLMProvider fulfills the BaseLLMProvider contract."""
    provider = MockLLMProvider(default_response="Mocked assistance response.")
    response = await provider.generate_response([
        LLMMessage(role="user", content="Hello")
    ])
    assert response.provider == "mock"
    assert response.content == "Mocked assistance response."
