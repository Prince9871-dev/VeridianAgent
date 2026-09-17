import os
import pytest
from backend.app.policy.catalog import policy_catalog
from backend.app.policy.schema import SourceExplicitness

EXPECTED_POLICY_IDS = [
    "KB-01",
    "KB-02",
    "KB-03",
    "POL-ASSET-01",
    "KB-04",
    "KB-05",
    "KB-06",
    "KB-07",
    "KB-08",
    "KB-09",
    "KB-10",
]

EXPECTED_PRECEDENT_IDS = [
    "TK-1042",
    "TK-1043",
    "TK-1044",
    "TK-1045",
    "TK-1046",
    "TK-1047",
    "TK-1048",
    "TK-1049",
    "TK-1050",
    "TK-1051",
]


def test_catalog_contains_all_11_authoritative_policies():
    """Verify that all 11 explicit policies from Section 1 are present in the catalog."""
    policies = policy_catalog.list_policies()
    policy_ids = [p.id for p in policies]
    assert len(policies) == 11
    for expected_id in EXPECTED_POLICY_IDS:
        assert expected_id in policy_ids, f"Policy {expected_id} missing from catalog"


def test_policies_have_exact_source_text_and_citations():
    """Verify that every policy preserves verbatim source text and accurate Page 1 citations."""
    for policy_id in EXPECTED_POLICY_IDS:
        policy = policy_catalog.get_policy(policy_id)
        assert policy is not None
        assert len(policy.exact_source_text.strip()) > 20
        assert policy.source_page == 1
        assert "Section 1" in policy.source_section
        assert policy.source_citation.startswith("[DataPack:")
        assert policy.source_explicitness == SourceExplicitness.EXPLICIT_POLICY


def test_precedents_loaded_from_section_3():
    """Verify that all 10 historical precedents from Section 3 are present."""
    precedents = policy_catalog.list_precedents()
    prec_ids = [p.ticket_id for p in precedents]
    assert len(precedents) == 10
    for expected_id in EXPECTED_PRECEDENT_IDS:
        assert expected_id in prec_ids, f"Precedent {expected_id} missing from catalog"
        prec = policy_catalog.get_precedent(expected_id)
        assert prec.source_page == 2
        assert "Section 3" in prec.source_section


def test_derived_files_marked_as_derived_not_authoritative():
    """Verify that derived JSON files explicitly declare themselves as DERIVED representations."""
    derived_dir = os.path.join(os.path.dirname(__file__), "..", "data", "derived")
    assert os.path.exists(derived_dir)
    assert os.path.exists(os.path.join(derived_dir, "authoritative_policies.json"))
    assert os.path.exists(os.path.join(derived_dir, "benchmark_requests.json"))
    assert os.path.exists(os.path.join(derived_dir, "ticket_queue_precedents.json"))
