"""
RecoveryOS — Webhook Events Repository
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from backend.db.connection import get_pool
from backend.domain.enums import WebhookProcessingStatus

logger = logging.getLogger(__name__)


class WebhooksRepository:

    async def record_event(
        self,
        provider: str,
        external_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_valid: bool,
    ) -> str | None:
        """
        Record an incoming webhook event.
        Returns event_id if newly inserted, None if already exists (duplicate).
        """
        pool = await get_pool()
        event_id = str(uuid.uuid4())
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO webhook_events (
                        id, provider, external_event_id, event_type,
                        payload, signature_valid, processing_status, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    """,
                    event_id,
                    provider,
                    external_event_id,
                    event_type,
                    _to_jsonb(payload),
                    signature_valid,
                    WebhookProcessingStatus.RECEIVED.value,
                )
                return event_id
            except Exception:
                # Duplicate external_event_id → already processed
                return None

    async def mark_processed(self, event_id: str) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE webhook_events
                SET processing_status = $1, processed_at = NOW()
                WHERE id = $2
                """,
                WebhookProcessingStatus.PROCESSED.value,
                event_id,
            )

    async def mark_failed(self, event_id: str) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE webhook_events
                SET processing_status = $1
                WHERE id = $2
                """,
                WebhookProcessingStatus.FAILED.value,
                event_id,
            )

    async def is_duplicate(self, external_event_id: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM webhook_events WHERE external_event_id = $1",
                external_event_id,
            )
        return row is not None


def _to_jsonb(data: dict[str, Any]) -> str:
    import json
    return json.dumps(data, default=str)
