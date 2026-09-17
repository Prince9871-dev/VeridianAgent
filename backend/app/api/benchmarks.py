import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.models.common import APIResponse, WorkflowAction
from backend.app.models.request import EmployeeMessage
from backend.app.agent.coordinator import agent_coordinator
from backend.app.agent.session import session_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])

BENCHMARK_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "derived"
    / "benchmark_requests.json"
)


class BenchmarkCaseResult(BaseModel):
    request_id: str
    employee_name: str
    employee_id: str
    request_text: str
    expected_workflow_action: str
    actual_workflow_action: str
    matched_policy_id: Optional[str] = None
    source_citation: Optional[str] = None
    ticket_id: Optional[str] = None
    is_conforming: bool
    latency_ms: float
    authoritative_rule_outcome: str


class BenchmarkSummary(BaseModel):
    total_cases: int
    conforming_cases: int
    conformance_rate: str
    conformance_summary: str
    results: List[BenchmarkCaseResult]


@router.get("/cases", response_model=APIResponse[Dict[str, Any]])
async def get_benchmark_cases() -> APIResponse[Dict[str, Any]]:
    """Get metadata about the 15 benchmark test cases."""
    if not os.path.exists(BENCHMARK_PATH):
        raise HTTPException(
            status_code=500, detail=f"Benchmark fixture not found at {BENCHMARK_PATH}"
        )
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("benchmarks", [])
    return APIResponse(
        success=True,
        message=f"Retrieved {len(cases)} benchmark cases",
        data={
            "total_cases": len(cases),
            "description": data.get("description", "Benchmark cases"),
            "cases": cases,
        },
    )


@router.post("/run", response_model=APIResponse[BenchmarkSummary])
async def run_benchmark_suite() -> APIResponse[BenchmarkSummary]:
    """
    Execute all 15 benchmark requests through the end-to-end AgentCoordinator.
    Real runtime flow:
    Frontend -> Benchmark API -> AgentCoordinator -> LLM Provider -> Session State ->
    Deterministic Policy Engine -> Ticket/Audit -> Benchmark Result.
    """
    if not os.path.exists(BENCHMARK_PATH):
        raise HTTPException(
            status_code=500, detail=f"Benchmark fixture not found at {BENCHMARK_PATH}"
        )

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmarks_data = json.load(f).get("benchmarks", [])

    results: List[BenchmarkCaseResult] = []
    conforming_count = 0

    for bm in benchmarks_data:
        req_id = bm["request_id"]
        session_id = f"benchmark-run-{req_id.lower()}-{int(time.time())}"
        session_store.reset(session_id)

        employee_id = bm.get("employee_id", f"EMP-{req_id}")
        msg = EmployeeMessage(
            session_id=session_id,
            employee_id=employee_id,
            content=bm["request_text"],
            metadata={"employee_name": bm["employee_name"], "benchmark_id": req_id},
        )

        start_t = time.perf_counter()
        response = await agent_coordinator.process_message(msg)
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

        actual_action = response.action.value
        expected_action = bm["expected_workflow_action"]
        is_conforming = actual_action == expected_action

        if is_conforming:
            conforming_count += 1

        policy_id = (
            response.policy_evaluation.policy_id
            if response.policy_evaluation
            else None
        )
        rule_outcome = (
            response.deterministic_evaluation.get("authoritative_rule_outcome", "UNKNOWN")
            if response.deterministic_evaluation
            else "UNKNOWN"
        )

        results.append(
            BenchmarkCaseResult(
                request_id=req_id,
                employee_name=bm["employee_name"],
                employee_id=employee_id,
                request_text=bm["request_text"],
                expected_workflow_action=expected_action,
                actual_workflow_action=actual_action,
                matched_policy_id=policy_id,
                source_citation=response.source_citation,
                ticket_id=response.ticket.id if response.ticket else None,
                is_conforming=is_conforming,
                latency_ms=elapsed_ms,
                authoritative_rule_outcome=rule_outcome,
            )
        )

    total = len(results)
    percentage = f"{round((conforming_count / total) * 100, 1)}%" if total > 0 else "0%"
    summary_text = f"{conforming_count}/{total} benchmark cases passed ({percentage} benchmark conformance)"

    summary = BenchmarkSummary(
        total_cases=total,
        conforming_cases=conforming_count,
        conformance_rate=percentage,
        conformance_summary=summary_text,
        results=results,
    )

    return APIResponse(
        success=True,
        message=summary_text,
        data=summary,
    )
