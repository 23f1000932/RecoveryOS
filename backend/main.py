"""
RecoveryOS — FastAPI Application Entry Point

Architecture:
  React/Vite frontend → REST/JSON → FastAPI (this file) → Supabase PostgreSQL
                                                         → Gemini API
                                                         → Razorpay Test Mode

Do not add business logic here. This file only wires routers and lifecycle events.
"""

import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.db.connection import close_db, init_db
from backend.domain.schemas import ErrorDetail, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Lifecycle (lifespan) ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RecoveryOS starting up — environment: %s", settings.environment)
    try:
        await init_db()
        logger.info("Startup complete — database connected.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Database connection failed at startup: %s. "
            "Server will start without DB — all DB-dependent endpoints will "
            "return empty responses (Rule 4: Safe failure).",
            exc,
        )
    yield
    await close_db()
    logger.info("RecoveryOS shut down.")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RecoveryOS",
    description="AI Revenue Recovery Orchestrator — Razorpay AI Buildathon",
    version=settings.api_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers (architecture §28, §32) ─────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Format HTTPExceptions into standard ErrorResponse schema."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    error_resp = ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=str(exc.detail),
            details={},
        )
    )
    return JSONResponse(status_code=exc.status_code, content=error_resp.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format validation errors into standard ErrorResponse schema."""
    errors_summary = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    error_resp = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request parameter validation failed.",
            details={"errors": errors_summary},
        )
    )
    return JSONResponse(status_code=422, content=error_resp.model_dump())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leaks stack traces (§28)."""
    logger.exception("Unhandled server exception: %s", exc)
    error_resp = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            details={},
        )
    )
    return JSONResponse(status_code=500, content=error_resp.model_dump())


# ── Routers ───────────────────────────────────────────────────────────────────
from backend.api.health import router as health_router
from backend.api.dashboard import router as dashboard_router
from backend.api.recovery_cases import router as cases_router
from backend.api.simulator import router as simulator_router
from backend.api.policies import router as policies_router

app.include_router(health_router)
app.include_router(dashboard_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(simulator_router, prefix="/api")
app.include_router(policies_router, prefix="/api")

from backend.api.webhooks import router as webhooks_router
app.include_router(webhooks_router)
