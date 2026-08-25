"""
RecoveryOS — Health Endpoint
"""

from fastapi import APIRouter

from backend.config import get_settings
from backend.domain.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    System health check.
    Returns 200 if the API is running.
    Does not check DB connectivity (use /health/db for that).
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.api_version,
        environment=settings.environment,
    )
