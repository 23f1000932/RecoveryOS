"""
RecoveryOS — Database Schema Migration Helper
Ensures all required columns and tables from backend/db/schema.sql exist in the live database.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.connection import get_pool, init_db, close_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_migrate")

MIGRATIONS = [
    """
    ALTER TABLE experiment_runs
    ADD COLUMN IF NOT EXISTS approvals_required INT NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE experiment_runs
    ADD COLUMN IF NOT EXISTS do_nothing_count INT NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE experiment_runs
    ADD COLUMN IF NOT EXISTS escalations INT NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE experiment_runs
    ADD COLUMN IF NOT EXISTS guardrail_stops INT NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE experiment_cases
    DROP CONSTRAINT IF EXISTS experiment_cases_case_id_fkey;
    """,
]

async def run_migrations():
    logger.info("Connecting to database...")
    await init_db()
    pool = await get_pool()
    async with pool.acquire() as conn:
        for sql in MIGRATIONS:
            logger.info("Executing migration: %s", sql.strip())
            await conn.execute(sql)
        
        # Verify columns in experiment_runs
        columns = await conn.fetch(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'experiment_runs';
            """
        )
        logger.info("Columns in experiment_runs: %s", [c['column_name'] for c in columns])
    await close_db()
    logger.info("Migrations completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_migrations())
