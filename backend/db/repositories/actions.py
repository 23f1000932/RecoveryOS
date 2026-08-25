"""
RecoveryOS — Actions Repository (recovery_actions table)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.db.connection import get_pool
from backend.domain.enums import ActionExecutionStatus, ActionType

logger = logging.getLogger(__name__)


class ActionsRepository:

    async def create_action(
        self,
        case_id: str,
        action: ActionType,
        idempotency_key: str,
        attempt_number: int = 1,
    ) -> str:
        """
        Create a recovery action record.
        Idempotency: if key already exists, returns existing action_id.
        """
        pool = await get_pool()
        action_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            # Try insert; if idempotency key exists, fetch existing
            try:
                await conn.execute(
                    """
                    INSERT INTO recovery_actions (
                        id, case_id, action, idempotency_key, status,
                        attempt_number, requested_at, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    """,
                    action_id,
                    case_id,
                    action.value,
                    idempotency_key,
                    ActionExecutionStatus.PENDING.value,
                    attempt_number,
                )
            except Exception:
                # Idempotency conflict — fetch existing
                row = await conn.fetchrow(
                    "SELECT id FROM recovery_actions WHERE idempotency_key = $1",
                    idempotency_key,
                )
                if row:
                    return str(row["id"])
                raise
        return action_id

    async def get_action(self, action_id: str) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM recovery_actions WHERE id = $1", action_id
            )
        return dict(row) if row else None

    async def get_by_idempotency_key(
        self, idempotency_key: str
    ) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM recovery_actions WHERE idempotency_key = $1",
                idempotency_key,
            )
        return dict(row) if row else None

    async def update_execution_result(
        self,
        action_id: str,
        status: ActionExecutionStatus,
        recovered_amount: Decimal,
        cost: Decimal,
        provider_reference: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE recovery_actions SET
                    status = $1,
                    executed_at = NOW(),
                    result = $2,
                    recovered_amount = $3,
                    cost = $4,
                    provider_reference = $5,
                    error_code = $6,
                    error_message = $7
                WHERE id = $8
                """,
                status.value,
                status.value,
                recovered_amount,
                cost,
                provider_reference,
                error_code,
                error_message,
                action_id,
            )

    async def list_actions_for_case(self, case_id: str) -> list[dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM recovery_actions WHERE case_id = $1 ORDER BY created_at ASC",
                case_id,
            )
        return [dict(r) for r in rows]
