"""
RecoveryOS — Database Connection

Manages the asyncpg connection pool for Supabase PostgreSQL.
Fail-closed: if DB is unavailable, operations raise immediately rather than
proceeding with incomplete state.
"""

from __future__ import annotations

import logging

import asyncpg

from backend.config import get_settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """
    Return the shared connection pool.
    Raises RuntimeError if DB is not configured.
    """
    global _pool
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialized. Call init_db() at application startup."
        )
    return _pool


def db_available() -> bool:
    """Return True if the DB pool has been initialised, False otherwise.

    Use this in API endpoints to return graceful empty responses when
    no DATABASE_URL is configured (Rule 4 — Safe failure).
    """
    return _pool is not None


async def init_db() -> None:
    """
    Initialize the asyncpg connection pool.
    Called once at FastAPI startup.
    """
    global _pool
    settings = get_settings()

    if not settings.database_available:
        logger.warning(
            "DATABASE_URL not configured. Database operations will fail. "
            "Set DATABASE_URL in .env to enable persistence."
        )
        return

    try:
        # Convert SQLAlchemy-style URL to raw postgres URL for asyncpg
        url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg2://", "postgresql://")

        _pool = await asyncpg.create_pool(
            dsn=url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database connection pool initialized.")
    except Exception as exc:
        logger.error("Failed to initialize database pool: %s", exc)
        raise


async def close_db() -> None:
    """Close the connection pool. Called at FastAPI shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


async def get_connection() -> asyncpg.Connection:
    """
    Acquire a connection from the pool.
    Used as a FastAPI dependency or direct context manager.
    """
    pool = await get_pool()
    return await pool.acquire()
