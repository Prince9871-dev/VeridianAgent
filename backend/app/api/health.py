import os
from fastapi import APIRouter
from backend.app.config import get_settings
from backend.app.models.common import APIResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check verifying service status and environment settings."""
    datapack_exists = os.path.exists(settings.datapack_path)
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "datapack_configured": datapack_exists,
        "datapack_path": settings.datapack_path,
    }
