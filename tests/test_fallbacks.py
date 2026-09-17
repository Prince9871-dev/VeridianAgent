import pytest
from backend.app.models.common import WorkflowAction
from backend.app.policy.fallbacks import (
    handle_no_applicable_policy,
    handle_unclear_input,
    handle_insufficient_information,
)
from backend.app.policy.schema import SourceExplicitness


def test_no_applicable_policy_fallback():
    """Verify fallback for completely out-of-scope requests."""
    result = handle_no_applicable_policy("Can I charter a corporate helicopter?")
    assert result.matched_policy_id is None
    assert len(result.matched_policy_ids) == 0
    assert len(result.authoritative_citations) == 0
    assert result.is_engineering_fallback is True
    assert result.fallback_type == "NO_APPLICABLE_POLICY"
    assert result.source_explicitness == SourceExplicitness.ENGINEERING_FALLBACK
    assert result.workflow_action == WorkflowAction.ESCALATE


def test_unclear_input_fallback():
    """Verify fallback for completely vague inputs (e.g. REQ-15)."""
    result = handle_unclear_input("hey can you help, its not working")
    assert result.matched_policy_id is None
    assert len(result.authoritative_citations) == 0
    assert result.is_engineering_fallback is True
    assert result.fallback_type == "UNCLEAR_INPUT"
    assert result.source_explicitness == SourceExplicitness.ENGINEERING_FALLBACK
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP


def test_insufficient_information_fallback():
    """Verify fallback when policy applies but required parameter is absent."""
    result = handle_insufficient_information(
        policy_id="KB-05",
        missing_fields=["printer_asset_tag"],
        prompt_message="Please provide printer asset tag.",
    )
    assert result.matched_policy_id == "KB-05"
    assert result.is_engineering_fallback is True
    assert result.fallback_type == "INSUFFICIENT_INFORMATION"
    assert result.workflow_action == WorkflowAction.ASK_FOLLOW_UP
    assert "printer_asset_tag" in result.missing_information
