"""
RecoveryOS — Merchants Repository
"""

from __future__ import annotations

from typing import Any

from backend.db.connection import get_pool

DEFAULT_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


class MerchantsRepository:

    async def get_merchant(self, merchant_id: str) -> dict[str, Any] | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM merchants WHERE id = $1", merchant_id
            )
        return dict(row) if row else None

    async def get_default_merchant(self) -> dict[str, Any] | None:
        return await self.get_merchant(DEFAULT_MERCHANT_ID)
