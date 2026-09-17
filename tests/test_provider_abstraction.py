import pytest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

from backend.app.agent.base import BaseLLMProvider, LLMMessage
from backend.app.agent.providers.mock import MockLLMProvider
from backend.app.agent.providers.gemini import GeminiProvider, ProviderUnavailableError
from backend.app.agent.providers.openai import OpenAIProvider
from backend.app.agent.factory import get_llm_provider
from backend.app.agent.coordinator import AgentCoordinator
from backend.app.models.request import IntentAnalysis, EmployeeMessage
from backend.app.models.common import WorkflowAction


@pytest.mark.asyncio
async def test_mock_provider_offline_contract():
    """Verify MockLLMProvider operates 100% offline and conforms to BaseLLMProvider."""
    provider = MockLLMProvider()
    assert isinstance(provider, BaseLLMProvider)

    # Completion
    messages = [LLMMessage(role="user", content="How do I reset my password?")]
    res = await provider.generate_response(messages)
    assert res.provider == "mock"
    assert "Veridian IT" in res.content

    # Structured extraction
    analysis: IntentAnalysis = await provider.extract_structured_data(
        prompt="I am locked out after 5 attempts",
        schema=IntentAnalysis,
    )
    assert isinstance(analysis, IntentAnalysis)
    assert analysis.candidate_policy_id == "KB-01"
    assert analysis.extracted_facts.get("is_locked_out") is True
    # Verify MockLLMProvider does NOT determine workflow actions like RESOLVE or CREATE_TICKET
    assert not hasattr(analysis, "action")


def test_provider_factory_resolution():
    """Verify get_llm_provider instantiates appropriate provider adapters."""
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockLLMProvider)

    gemini_p = get_llm_provider("gemini")
    assert isinstance(gemini_p, GeminiProvider)

    openai_p = get_llm_provider("openai")
    assert isinstance(openai_p, OpenAIProvider)

    # Unknown defaults to mock for offline safety
    fallback_p = get_llm_provider("unknown_vendor")
    assert isinstance(fallback_p, MockLLMProvider)


@pytest.mark.asyncio
async def test_gemini_missing_api_key_raises_provider_unavailable():
    """Verify GeminiProvider gracefully raises ProviderUnavailableError if API key missing."""
    provider = GeminiProvider(api_key=None)
    provider.api_key = None
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.extract_structured_data("test prompt", IntentAnalysis)
    assert "GEMINI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_missing_api_key_raises_provider_unavailable():
    """Verify OpenAIProvider gracefully raises ProviderUnavailableError if API key missing."""
    provider = OpenAIProvider(api_key=None)
    provider.api_key = None
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.extract_structured_data("test prompt", IntentAnalysis)
    assert "OPENAI_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_coordinator_handles_provider_unavailable_with_safe_fallback():
    """
    Constraint 10 & 12: If configured external provider fails or is unavailable,
    coordinator falls back safely to mock extractor rather than crashing or inventing decisions.
    """
    coordinator = AgentCoordinator()

    # Mock provider throwing ProviderUnavailableError
    failing_provider = AsyncMock()
    failing_provider.extract_structured_data.side_effect = ProviderUnavailableError("Simulated network outage")

    with patch("backend.app.agent.coordinator.get_llm_provider", return_value=failing_provider):
        req = EmployeeMessage(
            session_id="test-session-provider-fail",
            employee_id="EMP-9001",
            content="I need guest Wi-Fi for a visitor.",
        )
        # Should gracefully fall back to mock extraction and deterministic policy evaluation
        res = await coordinator.process_message(req)
        assert res is not None
        assert res.action == WorkflowAction.RESOLVE
        assert res.policy_evaluation.policy_id == "KB-07"


@pytest.mark.asyncio
async def test_coordinator_handles_malformed_llm_output():
    """
    Constraint 11 & 12: If LLM returns malformed data or fails extraction,
    coordinator catches the exception and falls back safely to default handling.
    """
    coordinator = AgentCoordinator()

    broken_provider = AsyncMock()
    broken_provider.extract_structured_data.side_effect = RuntimeError("Malformed JSON response from model")

    with patch("backend.app.agent.coordinator.get_llm_provider", return_value=broken_provider):
        req = EmployeeMessage(
            session_id="test-session-malformed",
            employee_id="EMP-9002",
            content="Something is totally broken and returning garbled text.",
        )
        res = await coordinator.process_message(req)
        assert res is not None
        # System does not crash, policy engine handles via fallback
        assert res.action in [WorkflowAction.ESCALATE, WorkflowAction.RESOLVE, WorkflowAction.ASK_FOLLOW_UP]
