from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.tickets import router as tickets_router
from backend.app.api.audit import router as audit_router
from backend.app.api.policies import router as policies_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(tickets_router)
api_router.include_router(audit_router)
api_router.include_router(policies_router)

