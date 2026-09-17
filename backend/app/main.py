from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.config import get_settings
from backend.app.api.router import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup: e.g. verify db connection or config
    yield
    # Shutdown: clean up any resources if needed


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise IT Service Agent for Veridian Corp - Phase 1 Foundation",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for Frontend Integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler ensuring standardized JSON error responses."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred.",
            "error_detail": str(exc) if settings.debug else "Internal Server Error",
        },
    )


# Include API v1 Router
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs_url": "/docs",
    }
