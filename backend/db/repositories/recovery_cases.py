"""
RecoveryOS — Recovery Cases Repository

All database access for the recovery_cases, action_candidates tables.
Business logic must not live here.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import asyncpg

from backend.db.connection import get_pool
from backend.domain.enums import ActionType, ApprovalStatus, CaseStatus

logger = logging.getLogger(__name__)

DEFAULT_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


class RecoveryCaseRepository:

    async def create_case(
        self,
        payment_id: str,
        customer_id: str,
        merchant_id: str,
        revenue_at_risk: Decimal,
        policy_version: str,
        expires_at: datetime | None = None,
    ) -> str:
        """Create a new recovery case. Returns case_id."""
        pool = await get_pool()
        case_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO recovery_cases (
                    id, merchant_id, payment_id, customer_id,
                    status, revenue_at_risk, policy_version,
                    requires_approval, approval_status,
                    expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                """,
                case_id,
                merchant_id,
                payment_id,
                customer_id,
                CaseStatus.CREATED.value,
                revenue_at_risk,
                policy_version,
                False,
                ApprovalStatus.NOT_REQUIRED.value,
                expires_at,
            )
        logger.info("Created recovery case %s for payment %s", case_id, payment_id)
        return case_id

    async def get_case(self, case_id: str) -> dict[str, Any] | None:
        """Fetch a single case by ID."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM recovery_cases WHERE id = $1", case_id
            )
        return dict(row) if row else None

    async def get_case_by_payment(self, payment_id: str) -> dict[str, Any] | None:
        """Find the active recovery case for a payment."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM recovery_cases
                WHERE payment_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                payment_id,
            )
        return dict(row) if row else None

    async def list_cases(
        self,
        merchant_id: str = DEFAULT_MERCHANT_ID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List cases with optional status filter. Returns (cases, total_count)."""
        pool = await get_pool()
        offset = (page - 1) * page_size
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT * FROM recovery_cases
                    WHERE merchant_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    merchant_id, status, page_size, offset,
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM recovery_cases WHERE merchant_id = $1 AND status = $2",
                    merchant_id, status,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM recovery_cases
                    WHERE merchant_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    merchant_id, page_size, offset,
                )
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM recovery_cases WHERE merchant_id = $1",
                    merchant_id,
                )
        return [dict(r) for r in rows], count or 0

    async def transition_status(
        self,
        case_id: str,
        from_status: CaseStatus,
        to_status: CaseStatus,
    ) -> bool:
        """
        Atomically transition case status.
        Returns True if transition succeeded (row was updated).
        Returns False if case was not in expected from_status (concurrent conflict).
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE recovery_cases
                SET status = $1, updated_at = NOW()
                WHERE id = $2 AND status = $3
                """,
                to_status.value, case_id, from_status.value,
            )
        updated = result.split()[-1] != "0"
        if not updated:
            logger.warning(
                "Status transition failed for case %s: expected %s, got conflict",
                case_id, from_status.value,
            )
        return updated

    async def update_decision(
        self,
        case_id: str,
        selected_action: ActionType,
        expected_gross_recovery: Decimal,
        expected_net_revenue: Decimal,
        requires_approval: bool,
        approval_status: ApprovalStatus,
        model_name: str,
        model_version: str,
        policy_version: str,
        status: CaseStatus,
    ) -> None:
        """Store optimizer decision on the case."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE recovery_cases SET
                    selected_action = $1,
                    expected_gross_recovery = $2,
                    expected_net_revenue = $3,
                    requires_approval = $4,
                    approval_status = $5,
                    model_name = $6,
                    model_version = $7,
                    policy_version = $8,
                    status = $9,
                    updated_at = NOW()
                WHERE id = $10
                """,
                selected_action.value,
                expected_gross_recovery,
                expected_net_revenue,
                requires_approval,
                approval_status.value,
                model_name,
                model_version,
                policy_version,
                status.value,
                case_id,
            )

    async def update_approval(
        self,
        case_id: str,
        approval_status: ApprovalStatus,
        case_status: CaseStatus,
    ) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE recovery_cases SET
                    approval_status = $1,
                    status = $2,
                    updated_at = NOW()
                WHERE id = $3
                """,
                approval_status.value,
                case_status.value,
                case_id,
            )

    async def update_result(
        self,
        case_id: str,
        status: CaseStatus,
        actual_recovered: Decimal,
        intervention_cost: Decimal,
        incremental_recovery: Decimal,
        net_incremental_recovery: Decimal,
    ) -> None:
        """Record final recovery result."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE recovery_cases SET
                    status = $1,
                    actual_recovered = $2,
                    intervention_cost = $3,
                    incremental_recovery = $4,
                    net_incremental_recovery = $5,
                    updated_at = NOW()
                WHERE id = $6
                """,
                status.value,
                actual_recovered,
                intervention_cost,
                incremental_recovery,
                net_incremental_recovery,
                case_id,
            )

    async def save_action_candidates(
        self,
        case_id: str,
        candidates: list[dict[str, Any]],
    ) -> None:
        """Upsert action candidates for a case."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Delete existing candidates for this case first
            await conn.execute(
                "DELETE FROM action_candidates WHERE case_id = $1", case_id
            )
            for c in candidates:
                await conn.execute(
                    """
                    INSERT INTO action_candidates (
                        id, case_id, action, probability, model_confidence,
                        recoverable_amount, intervention_cost, incentive_cost, contact_cost,
                        expected_gross_recovery, expected_net_revenue,
                        allowed, blocked_reason, rank, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW()
                    )
                    """,
                    str(uuid.uuid4()),
                    case_id,
                    c["action"],
                    c["probability"],
                    c["confidence"],
                    c["recoverable_amount"],
                    c["intervention_cost"],
                    c["incentive_cost"],
                    c["contact_cost"],
                    c["expected_gross_recovery"],
                    c["expected_net_revenue"],
                    c["allowed"],
                    c.get("blocked_reason"),
                    c["rank"],
                )

    async def get_action_candidates(self, case_id: str) -> list[dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM action_candidates WHERE case_id = $1 ORDER BY rank ASC",
                case_id,
            )
        return [dict(r) for r in rows]

    async def get_dashboard_summary(
        self,
        merchant_id: str = DEFAULT_MERCHANT_ID,
    ) -> dict[str, Any]:
        """Aggregate dashboard metrics from recovery_cases."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM(revenue_at_risk), 0)           AS revenue_at_risk,
                    COALESCE(SUM(actual_recovered), 0)           AS revenue_recovered,
                    COALESCE(SUM(intervention_cost), 0)          AS intervention_spend,
                    COALESCE(SUM(incremental_recovery), 0)       AS incremental_recovery,
                    COALESCE(SUM(net_incremental_recovery), 0)   AS net_incremental_recovery,
                    COUNT(*)                                      AS total_cases,
                    COUNT(*) FILTER (WHERE status = 'RECOVERED') AS recovered_cases,
                    COUNT(*) FILTER (WHERE status = 'STOPPED' AND selected_action = 'do_nothing') AS do_nothing_count,
                    COUNT(*) FILTER (WHERE status = 'ESCALATED') AS escalations,
                    COUNT(*) FILTER (WHERE status = 'PENDING_APPROVAL') AS pending_approval_count
                FROM recovery_cases
                WHERE merchant_id = $1
                """,
                merchant_id,
            )
        return dict(row) if row else {}
