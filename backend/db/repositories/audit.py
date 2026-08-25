"""
RecoveryOS — Audit Log Repository
"""

from __future__ import annotations

import logging
from typing import Any

from backend.db.connection import get_pool
from backend.domain.models import AuditEntry

logger = logging.getLogger(__name__)


class AuditRepository:

    async def write(self, entry: AuditEntry) -> None:
        """Append one audit event. Never raises — audit must not break the pipeline."""
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (
                        id, case_id, event_type, actor, source,
                        input_snapshot, output_snapshot, decision, guardrail_result,
                        model_name, model_version, policy_version, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    entry.id,
                    entry.case_id,
                    entry.event_type.value,
                    entry.actor,
                    entry.source.value,
                    _to_jsonb(entry.input_snapshot),
                    _to_jsonb(entry.output_snapshot),
                    _to_jsonb(entry.decision) if entry.decision else None,
                    _to_jsonb(entry.guardrail_result) if entry.guardrail_result else None,
                    entry.model_name,
                    entry.model_version,
                    entry.policy_version,
                    entry.timestamp,
                )
        except Exception as exc:
            logger.error("Failed to write audit entry for case %s: %s", entry.case_id, exc)

    async def get_case_audit(self, case_id: str) -> list[dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM audit_logs
                WHERE case_id = $1
                ORDER BY timestamp ASC
                """,
                case_id,
            )
        return [dict(r) for r in rows]


def _to_jsonb(data: dict[str, Any] | None) -> str | None:
    """Convert dict to JSON string for asyncpg JSONB parameter."""
    import json
    if data is None:
        return None
    return json.dumps(data, default=str)
