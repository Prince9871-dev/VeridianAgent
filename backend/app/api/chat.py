import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from backend.app.models.common import APIResponse
from backend.app.models.request import EmployeeMessage, ServiceAgentResponse
from backend.app.agent.session import session_store, SessionState
from backend.app.agent.coordinator import agent_coordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=APIResponse[ServiceAgentResponse])
async def send_message(message: EmployeeMessage) -> APIResponse[ServiceAgentResponse]:
    """
    Process an employee message through the Veridian Assist Coordinator:
    1. LLM NLU fact extraction (non-authoritative)
    2. Multi-turn fact accumulation
    3. Deterministic Policy Engine evaluation (sole authority)
    4. Workflow dispatch & optional ticket creation
    5. Append-only audit logging
    """
    try:
        response = await agent_coordinator.process_message(message)
        return APIResponse(
            success=True,
            message="Message processed successfully",
            data=response,
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/sessions/{session_id}", response_model=APIResponse[SessionState])
async def get_session(
    session_id: str = Path(..., description="Unique conversation session ID")
) -> APIResponse[SessionState]:
    """Retrieve session state, conversation history, and accumulated facts."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return APIResponse(
        success=True,
        message=f"Retrieved session {session_id}",
        data=session,
    )


@router.post("/sessions/{session_id}/reset", response_model=APIResponse[Dict[str, Any]])
async def reset_session(
    session_id: str = Path(..., description="Unique conversation session ID to reset")
) -> APIResponse[Dict[str, Any]]:
    """Reset a conversation session and clear accumulated facts."""
    session_store.reset(session_id)
    return APIResponse(
        success=True,
        message=f"Session '{session_id}' reset successfully",
        data={"session_id": session_id, "status": "RESET"},
    )
