"""
RecoveryOS — Customers Repository
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from backend.db.connection import get_pool

logger = logging.getLogger(__name__)


class CustomersRepository:

    async def create_customer(
        self,
        merchant_id: str,
        transaction_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        avg_amount: Decimal = Decimal("0"),
        preferred_method: str = "card",
    ) -> str:
        """Create a customer record. Returns customer_id."""
        pool = await get_pool()
        customer_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO customers (
                    id, merchant_id, transaction_count, success_count,
                    failure_count, avg_amount, preferred_method,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                customer_id, merchant_id, transaction_count, success_count,
                failure_count, avg_amount, preferred_method,
            )
        return customer_id

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM customers WHERE id = $1", customer_id
            )
        return dict(row) if row else None

    async def get_retry_count_for_case(
        self, customer_id: str, case_id: str
    ) -> int:
        """Count successful retry actions for this customer in this case."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM recovery_actions ra
                JOIN recovery_cases rc ON rc.id = ra.case_id
                WHERE rc.customer_id = $1
                  AND ra.case_id = $2
                  AND ra.action IN ('retry_now', 'retry_later')
                  AND ra.status != 'failed'
                """,
                customer_id, case_id,
            )
        return count or 0

    async def get_message_count_for_case(
        self, customer_id: str, case_id: str
    ) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM recovery_actions ra
                JOIN recovery_cases rc ON rc.id = ra.case_id
                WHERE rc.customer_id = $1
                  AND ra.case_id = $2
                  AND ra.action = 'reminder'
                  AND ra.status != 'failed'
                """,
                customer_id, case_id,
            )
        return count or 0

    async def get_incentive_amount_for_case(
        self, customer_id: str, case_id: str
    ) -> Decimal:
        pool = await get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                """
                SELECT COALESCE(SUM(ra.cost), 0)
                FROM recovery_actions ra
                JOIN recovery_cases rc ON rc.id = ra.case_id
                WHERE rc.customer_id = $1
                  AND ra.case_id = $2
                  AND ra.action = 'incentive'
                  AND ra.status != 'failed'
                """,
                customer_id, case_id,
            )
        return Decimal(str(total or 0))

    async def get_daily_incentive_spend(self, merchant_id: str) -> Decimal:
        """Total incentive cost paid out today for this merchant."""
        pool = await get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                """
                SELECT COALESCE(SUM(ra.cost), 0)
                FROM recovery_actions ra
                JOIN recovery_cases rc ON rc.id = ra.case_id
                WHERE rc.merchant_id = $1
                  AND ra.action = 'incentive'
                  AND ra.status = 'success'
                  AND ra.executed_at >= CURRENT_DATE
                """,
                merchant_id,
            )
        return Decimal(str(total or 0))
