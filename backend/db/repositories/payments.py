"""
RecoveryOS — Payments Repository
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from backend.db.connection import get_pool

logger = logging.getLogger(__name__)

DEFAULT_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


class PaymentsRepository:

    async def create_payment(
        self,
        merchant_id: str,
        customer_id: str,
        external_payment_id: str,
        amount: Decimal,
        currency: str,
        method: str,
        status: str,
        failure_code: str,
        attempt_number: int,
    ) -> str:
        """Create a payment record. Returns payment_id."""
        pool = await get_pool()
        payment_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO payments (
                    id, merchant_id, customer_id, external_payment_id,
                    amount, currency, method, status, failure_code,
                    attempt_number, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                ON CONFLICT (external_payment_id) DO NOTHING
                """,
                payment_id, merchant_id, customer_id, external_payment_id,
                amount, currency, method, status, failure_code, attempt_number,
            )
        return payment_id

    async def get_payment(self, payment_id: str) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM payments WHERE id = $1", payment_id
            )
        return dict(row) if row else None

    async def get_payment_by_external_id(
        self, external_payment_id: str
    ) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM payments WHERE external_payment_id = $1",
                external_payment_id,
            )
        return dict(row) if row else None

    async def update_status(self, payment_id: str, status: str) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE payments SET status = $1, updated_at = NOW() WHERE id = $2",
                status, payment_id,
            )
