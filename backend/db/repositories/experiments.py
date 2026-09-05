"""
RecoveryOS — Experiments Repository (simulator)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.db.connection import get_pool
from backend.domain.models import ExperimentCase, ExperimentMetrics

logger = logging.getLogger(__name__)


class ExperimentsRepository:

    async def create_experiment(self, metrics: ExperimentMetrics) -> str:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO experiment_runs (
                    id, seed, dataset_size, baseline_policy, ai_policy,
                    baseline_recovered, ai_recovered, baseline_cost, ai_cost,
                    incremental_recovery, net_incremental_recovery,
                    baseline_recovery_rate, ai_recovery_rate,
                    guardrail_stops, escalations, do_nothing_count,
                    approvals_required,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
                """,
                metrics.experiment_id,
                metrics.seed,
                metrics.dataset_size,
                metrics.baseline_policy,
                metrics.ai_policy,
                metrics.baseline_recovered,
                metrics.ai_recovered,
                metrics.baseline_cost,
                metrics.ai_cost,
                metrics.incremental_recovery,
                metrics.net_incremental_recovery,
                metrics.baseline_recovery_rate,
                metrics.ai_recovery_rate,
                metrics.guardrail_stops,
                metrics.escalations,
                metrics.do_nothing_count,
                metrics.approvals_required,
                metrics.created_at,
            )
        return metrics.experiment_id

    async def save_experiment_cases(
        self,
        experiment_id: str,
        cases: list[ExperimentCase],
    ) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            for c in cases:
                await conn.execute(
                    """
                    INSERT INTO experiment_cases (
                        id, experiment_id, case_id,
                        baseline_action, baseline_success, baseline_recovered,
                        ai_action, ai_success, ai_recovered, ai_cost,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                    """,
                    str(uuid.uuid4()),
                    experiment_id,
                    c.case_id,
                    c.baseline_action.value,
                    c.baseline_success,
                    c.baseline_recovered,
                    c.ai_action.value,
                    c.ai_success,
                    c.ai_recovered,
                    c.ai_cost,
                )

    async def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM experiment_runs WHERE id = $1", experiment_id
            )
        return dict(row) if row else None

    async def get_experiment_cases(
        self, experiment_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM experiment_cases
                WHERE experiment_id = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                experiment_id, limit,
            )
        return [dict(r) for r in rows]

    async def list_experiments(self, limit: int = 20) -> list[dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM experiment_runs ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [dict(r) for r in rows]
