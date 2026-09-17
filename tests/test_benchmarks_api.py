"""
Test for the Benchmark API endpoint.
Verifies real end-to-end execution through FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_benchmark_cases():
    """Verify /cases endpoint returns 15 cases and fixture info."""
    response = client.get("/api/v1/benchmarks/cases")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    data = res_json["data"]
    assert data["total_cases"] == 15
    assert len(data["cases"]) == 15
    assert data["cases"][0]["request_id"] == "REQ-01"


def test_run_benchmarks_live():
    """Verify live benchmark execution returns 15/15 conforming cases."""
    response = client.post("/api/v1/benchmarks/run")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    data = res_json["data"]
    assert data["total_cases"] == 15
    assert data["conforming_cases"] == 15
    assert data["conformance_rate"] == "100.0%"
    assert "15/15 benchmark cases passed" in data["conformance_summary"]
    assert len(data["results"]) == 15

    # Check first case
    req1 = data["results"][0]
    assert req1["request_id"] == "REQ-01"
    assert req1["is_conforming"] is True
    assert req1["expected_workflow_action"] == "CREATE_TICKET"
    assert req1["actual_workflow_action"] == "CREATE_TICKET"
    assert req1["matched_policy_id"] == "KB-03"
