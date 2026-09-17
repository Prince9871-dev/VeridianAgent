from typing import List, Optional
from fastapi import APIRouter, Query
from backend.app.models.common import APIResponse
from backend.app.models.audit import AuditEvent
from backend.app.audit.logger import audit_logger

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=APIResponse[List[AuditEvent]])
async def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session_id: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
):
    """Retrieve immutable audit log events with optional filtering."""
    events = await audit_logger.list_events(
        limit=limit,
        offset=offset,
        session_id=session_id,
        employee_id=employee_id,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(events)} audit events",
        data=events,
    )
