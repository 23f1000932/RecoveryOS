"""
RecoveryOS — Razorpay Webhook Handler

POST /webhooks/razorpay

Processing flow (§20–21 of architecture):
  1. Read raw body bytes (before JSON parse — needed for HMAC)
  2. Verify HMAC-SHA256 signature against RAZORPAY_WEBHOOK_SECRET
  3. If invalid → return 200 OK (never 401 — prevents enumeration)
  4. Parse event JSON
  5. Deduplicate via WebhooksRepository.is_duplicate()
  6. Insert webhook_events row
  7. If event_type == "payment.failed" → run RecoveryPipeline
  8. Mark event processed
  9. Return 200 OK (always — Razorpay retries on non-2xx)

Rule 4 (Safe failure):
  Any unhandled exception must be caught, logged, and still return 200.
  A non-200 tells Razorpay to retry — which would cause duplicate processing.

Rule 5 (Idempotency):
  WebhooksRepository.record_event() uses external_event_id UNIQUE key.
  If already processed, returns None → we return 200 immediately.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Request, Response

from backend.config import get_settings
from backend.db.repositories.webhooks import WebhooksRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

MERCHANT_ID_FALLBACK = "00000000-0000-0000-0000-000000000001"


# ── Signature Validation ───────────────────────────────────────────────────────

def _verify_razorpay_signature(body: bytes, signature: str, webhook_secret: str) -> bool:
    """
    Validate Razorpay webhook HMAC-SHA256 signature.

    Razorpay computes: HMAC-SHA256(raw_body, webhook_secret)
    and sends it as X-Razorpay-Signature header.
    """
    if not webhook_secret or not signature:
        return False
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Payment Normalization ─────────────────────────────────────────────────────

def _normalize_payment_context(event_payload: dict) -> dict:
    """
    Extract payment fields from Razorpay event payload.

    Returns a flat dict with normalized keys for CaseContext construction.
    """
    payment = event_payload.get("payload", {}).get("payment", {}).get("entity", {})
    return {
        "external_payment_id": payment.get("id", ""),
        "amount": Decimal(str(payment.get("amount", 0))) / 100,  # paise → INR
        "currency": payment.get("currency", "INR"),
        "method": payment.get("method", "card"),
        "failure_code": payment.get("error_code", "unknown"),
        "failure_description": payment.get("error_description", ""),
        "email": payment.get("email", ""),
        "contact": payment.get("contact", ""),
        "merchant_id": payment.get("merchant_id", MERCHANT_ID_FALLBACK),
    }


# ── Background Pipeline Runner ────────────────────────────────────────────────

async def _run_pipeline_for_failed_payment(
    event_id: str,
    payment_context: dict,
    webhook_repo: WebhooksRepository,
) -> None:
    """
    Background task: run RecoveryPipeline for a payment.failed event.

    Errors are caught and logged — never propagated (would break 200 response).
    """
    try:
        from backend.db.connection import db_available
        from backend.orchestrator.recovery_pipeline import create_pipeline
        from backend.orchestrator.context import CaseContext
        from backend.domain.enums import ExecutionMode, PipelineSource

        if not db_available():
            logger.warning(
                "Webhook pipeline: DB unavailable — cannot process event %s", event_id
            )
            await webhook_repo.mark_failed(event_id)
            return

        # Build a minimal CaseContext from the payment payload
        # A real implementation would look up/create customer record here
        # For Phase 6: create a synthetic case_id based on payment ID
        external_payment_id = payment_context.get("external_payment_id", "")
        case_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"webhook:{external_payment_id}"))

        from backend.orchestrator.context import RecoveryPolicy
        policy = RecoveryPolicy(
            version="1.0",
            max_retries_per_customer=2,
            max_messages_per_customer=2,
            max_incentive_per_customer=Decimal("100"),
            daily_incentive_pool=Decimal("5000"),
            high_value_threshold=Decimal("10000"),
            min_expected_net_revenue=Decimal("100"),
            min_model_confidence=0.65,
            recovery_window_hours=48,
            auto_action_probability=0.70,
        )

        context = CaseContext(
            case_id=case_id,
            payment_id=external_payment_id,
            customer_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cust:{payment_context.get('contact', case_id)}")),
            merchant_id=payment_context.get("merchant_id", MERCHANT_ID_FALLBACK),
            amount=payment_context["amount"],
            currency=payment_context.get("currency", "INR"),
            method=payment_context.get("method", "card"),
            failure_code=payment_context.get("failure_code", "unknown"),
            attempt_number=1,
            customer_success_rate=0.50,        # unknown without DB lookup
            customer_transaction_count=1,
            customer_success_count=0,
            customer_failure_count=1,
            customer_avg_amount=payment_context["amount"],
            time_since_failure_hours=0.1,
            hour_of_day=12,
            day_of_week=1,
            previous_failure_count=0,
            policy=policy,
        )

        pipeline = create_pipeline(execution_mode=ExecutionMode.TEST_MODE)
        proposal = await pipeline.process_case(
            context,
            source=PipelineSource.WEBHOOK,
            execute=False,   # Phase 6: analyze only; execute=True for live mode
        )

        logger.info(
            "Webhook pipeline: event=%s case=%s action=%s enr=%.2f",
            event_id,
            case_id,
            proposal.recommended_action.value,
            proposal.optimization_result.selected_expected_net_revenue,
        )

        await webhook_repo.mark_processed(event_id)

    except Exception as exc:
        logger.error("Webhook pipeline: error processing event %s: %s", event_id, exc)
        try:
            await webhook_repo.mark_failed(event_id)
        except Exception:
            pass


# ── Webhook Endpoint ──────────────────────────────────────────────────────────

@router.post("/razorpay", status_code=200)
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """
    Receive Razorpay webhook events.

    Always returns 200. Razorpay will retry on any non-2xx response.
    Processing happens in a background task to avoid blocking the response.
    """
    settings = get_settings()
    body = await request.body()

    # ── 1. Signature validation ────────────────────────────────────────────────
    signature = request.headers.get("X-Razorpay-Signature", "")
    sig_valid = False

    if settings.razorpay_webhook_secret:
        sig_valid = _verify_razorpay_signature(body, signature, settings.razorpay_webhook_secret)
        if not sig_valid:
            logger.warning(
                "Webhook: invalid signature — rejecting event silently. "
                "sig=%r secret_prefix=%r",
                signature[:12] if signature else "MISSING",
                settings.razorpay_webhook_secret[:4] if settings.razorpay_webhook_secret else "MISSING",
            )
            # Return 200 silently — never expose signature mismatch to caller
            return Response(content='{"status":"ok"}', media_type="application/json")
    else:
        # No secret configured — accept but log warning (development only)
        logger.warning(
            "Webhook: RAZORPAY_WEBHOOK_SECRET not set — accepting without signature validation."
        )
        sig_valid = True

    # ── 2. Parse event ─────────────────────────────────────────────────────────
    try:
        event = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.error("Webhook: invalid JSON body: %s", exc)
        return Response(content='{"status":"ok"}', media_type="application/json")

    event_id = event.get("id", str(uuid.uuid4()))
    event_type = event.get("event", "unknown")

    # ── 3. Deduplicate ─────────────────────────────────────────────────────────
    webhook_repo = WebhooksRepository()

    try:
        from backend.db.connection import db_available
        if db_available():
            inserted_id = await webhook_repo.record_event(
                provider="razorpay",
                external_event_id=event_id,
                event_type=event_type,
                payload=event,
                signature_valid=sig_valid,
            )
            if inserted_id is None:
                # Duplicate — already processed
                logger.info("Webhook: duplicate event %s — returning 200 no-op.", event_id)
                return Response(content='{"status":"ok","duplicate":true}', media_type="application/json")
        else:
            inserted_id = event_id
            logger.warning(
                "Webhook: DB unavailable — skipping dedup for event %s", event_id
            )
    except Exception as exc:
        logger.error("Webhook: failed to record event %s: %s", event_id, exc)
        inserted_id = event_id

    # ── 4. Route event ─────────────────────────────────────────────────────────
    if event_type == "payment.failed":
        payment_context = _normalize_payment_context(event)
        logger.info(
            "Webhook: payment.failed event=%s amount=%.2f method=%s",
            event_id,
            payment_context.get("amount", 0),
            payment_context.get("method", "unknown"),
        )
        background_tasks.add_task(
            _run_pipeline_for_failed_payment,
            inserted_id,
            payment_context,
            webhook_repo,
        )
    else:
        logger.debug("Webhook: unhandled event_type=%s event_id=%s", event_type, event_id)
        # Mark non-payment events as processed immediately
        try:
            from backend.db.connection import db_available
            if db_available() and inserted_id:
                await webhook_repo.mark_processed(inserted_id)
        except Exception:
            pass

    return Response(content='{"status":"ok"}', media_type="application/json")
