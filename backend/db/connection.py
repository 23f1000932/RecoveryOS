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

        # Parse the URL manually using regex to work around Python 3.13's
        # stricter urllib.parse that rejects Supabase pooler hostnames.
        # Format: postgresql://user:pass@host:port/dbname[?query]
        import re
        _URL_RE = re.compile(
            r"postgresql(?:\+\w+)?://"
            r"(?P<user>[^:]+):(?P<pass>.+?)@"
            r"(?P<host>[^/:@]+):(?P<port>\d+)"
            r"/(?P<db>[^?]+)"
        )
        m = _URL_RE.match(url)
        if not m:
            raise ValueError(f"Cannot parse DATABASE_URL. Expected: postgresql://user:pass@host:port/db")

        db_user = m.group("user")
        db_pass = m.group("pass")
        db_host = m.group("host")
        db_port = int(m.group("port"))
        db_name = m.group("db")

        # Supabase connection pooler (transaction mode) requires:
        #   - ssl='require'  — TLS mandatory on pooler endpoint
        #   - statement_cache_size=0  — pooler doesn't support prepared statements
        _pool = await asyncpg.create_pool(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            min_size=1,
            max_size=10,
            command_timeout=30,
            ssl="require",
            statement_cache_size=0,
        )

        logger.info("Database connection pool initialized.")

        # Ensure schema migrations are applied
        try:
            async with _pool.acquire() as conn:
                await conn.execute(
                    """
                    ALTER TABLE experiment_runs
                    ADD COLUMN IF NOT EXISTS approvals_required INT NOT NULL DEFAULT 0;
                    ALTER TABLE experiment_cases
                    DROP CONSTRAINT IF EXISTS experiment_cases_case_id_fkey;
                    """
                )
        except Exception as mig_err:
            logger.warning("Auto-migration notice: %s", mig_err)
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
