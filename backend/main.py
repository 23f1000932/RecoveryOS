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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.db.connection import close_db, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RecoveryOS",
    description="AI Revenue Recovery Orchestrator — Razorpay AI Buildathon",
    version=settings.api_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
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


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_db()
    logger.info("RecoveryOS shut down.")


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
