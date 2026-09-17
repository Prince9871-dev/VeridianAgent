import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_chat_message_endpoint():
    """Verify POST /api/v1/chat/message processes request and returns ServiceAgentResponse."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "session_id": "api-session-001",
            "employee_id": "EMP-8001",
            "content": "Can I install a productivity tracking browser extension on my laptop?",
            "metadata": {"department": "Marketing"},
        }
        res = await client.post("/api/v1/chat/message", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        agent_resp = data["data"]
        assert agent_resp["session_id"] == "api-session-001"
        assert agent_resp["action"] in ["CREATE_TICKET", "ASK_FOLLOW_UP", "RESOLVE"]
        assert agent_resp["policy_evaluation"] is not None
        assert agent_resp["policy_evaluation"]["policy_id"] == "KB-04"
        assert "KB-04" in agent_resp["source_citation"]


@pytest.mark.asyncio
async def test_chat_session_lifecycle_endpoints():
    """Verify GET /api/v1/chat/sessions/{id} and POST /api/v1/chat/sessions/{id}/reset."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        session_id = "api-session-lifecycle-002"

        # Initially session should not exist
        res_not_found = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert res_not_found.status_code == 404

        # Post a message to create session
        msg_payload = {
            "session_id": session_id,
            "employee_id": "EMP-8002",
            "content": "I need guest Wi-Fi for our partners.",
        }
        await client.post("/api/v1/chat/message", json=msg_payload)

        # Now GET session must return 200 with conversation history
        res_get = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert res_get.status_code == 200
        session_data = res_get.json()["data"]
        assert session_data["session_id"] == session_id
        assert len(session_data["history"]) >= 2  # employee + agent

        # Reset session
        res_reset = await client.post(f"/api/v1/chat/sessions/{session_id}/reset")
        assert res_reset.status_code == 200
        assert res_reset.json()["data"]["status"] == "RESET"

        # Subsequent GET returns 404
        res_after_reset = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert res_after_reset.status_code == 404


@pytest.mark.asyncio
async def test_chat_message_validation_error():
    """Verify 422 error is returned when request body violates EmployeeMessage schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing 'content' and 'employee_id'
        invalid_payload = {"session_id": "bad-payload-session"}
        res = await client.post("/api/v1/chat/message", json=invalid_payload)
        assert res.status_code == 422
