"""
RecoveryOS — Demo Data Seeder

Seeds the 5 required demo cases (A–E) from architecture §36 into the DB.

Usage:
    .venv\\Scripts\\python scripts/seed_demo_data.py

Requirements:
    - DATABASE_URL must be set in .env
    - Run this AFTER applying backend/db/schema.sql via Supabase SQL Editor

All inserts use ON CONFLICT DO NOTHING so this script is idempotent.

Demo Cases:
    A  Standard recovery — retry_later, ₹3,000, high-success customer
    B  Do nothing        — ₹80, below ENR threshold, not worth intervening
    C  Guardrail block   — attempt #3 exceeds retry limit, reminder selected
    D  Approval required — ₹15,000, above high_value_threshold
    E  Dedup webhook     — seeds a webhook_events row to demo idempotency
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Demo IDs (stable so script stays idempotent) ──────────────────────────────

MERCHANT_ID     = "00000000-0000-0000-0000-000000000001"
CUSTOMER_A      = "00000000-0000-0000-0000-000000000010"
CUSTOMER_B      = "00000000-0000-0000-0000-000000000011"
CUSTOMER_C      = "00000000-0000-0000-0000-000000000012"
CUSTOMER_D      = "00000000-0000-0000-0000-000000000013"
CUSTOMER_E      = "00000000-0000-0000-0000-000000000014"

PAYMENT_A       = "00000000-0000-0000-0000-000000000020"
PAYMENT_B       = "00000000-0000-0000-0000-000000000021"
PAYMENT_C       = "00000000-0000-0000-0000-000000000022"
PAYMENT_D       = "00000000-0000-0000-0000-000000000023"
PAYMENT_E       = "00000000-0000-0000-0000-000000000024"

CASE_A          = "00000000-0000-0000-0000-000000000030"
CASE_B          = "00000000-0000-0000-0000-000000000031"
CASE_C          = "00000000-0000-0000-0000-000000000032"
CASE_D          = "00000000-0000-0000-0000-000000000033"
CASE_E          = "00000000-0000-0000-0000-000000000034"

WEBHOOK_EVENT_E = "demo-webhook-evt-00000000000000001"


async def seed():
    # ── Load .env ──────────────────────────────────────────────────────────────
    from dotenv import load_dotenv
    load_dotenv()

    if not os.environ.get("DATABASE_URL"):
        logger.error(
            "DATABASE_URL not set. Add it to .env before running this script."
        )
        sys.exit(1)

    from backend.db.connection import init_db, get_pool

    logger.info("Connecting to database…")
    await init_db()
    pool = await get_pool()

    async with pool.acquire() as conn:
        # ── Merchant ──────────────────────────────────────────────────────────
        logger.info("Seeding demo merchant…")
        await conn.execute("""
            INSERT INTO merchants (
                id, name, retry_limit, message_limit,
                max_incentive_per_customer, daily_incentive_pool,
                high_value_threshold, min_expected_net_revenue,
                min_model_confidence, recovery_window_hours,
                auto_action_probability
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (id) DO NOTHING
        """,
            MERCHANT_ID, "RecoveryOS Demo Merchant", 2, 2,
            Decimal("100.00"), Decimal("5000.00"),
            Decimal("10000.00"), Decimal("100.00"),
            0.65, 48, 0.70,
        )

        # ── Customers ─────────────────────────────────────────────────────────
        logger.info("Seeding demo customers…")
        customers = [
            (CUSTOMER_A, 25, 20, 5, Decimal("3500"), "card"),    # A: high-success
            (CUSTOMER_B, 8,  4,  4, Decimal("75"),   "upi"),     # B: low-value
            (CUSTOMER_C, 12, 6,  6, Decimal("4000"), "netbanking"),  # C: many failures
            (CUSTOMER_D, 30, 26, 4, Decimal("12000"), "card"),   # D: high-value
            (CUSTOMER_E, 15, 12, 3, Decimal("3000"), "upi"),     # E: normal
        ]
        for cid, tx_count, succ, fail, avg, method in customers:
            await conn.execute("""
                INSERT INTO customers (id, merchant_id, transaction_count, success_count,
                    failure_count, avg_amount, preferred_method)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
            """, cid, MERCHANT_ID, tx_count, succ, fail, avg, method)

        # ── Payments ──────────────────────────────────────────────────────────
        logger.info("Seeding demo payments…")
        payments = [
            (PAYMENT_A, CUSTOMER_A, "pay_demo_case_a", Decimal("3000"), "card",        "insufficient_funds", 1, "failed"),
            (PAYMENT_B, CUSTOMER_B, "pay_demo_case_b", Decimal("80"),   "upi",         "bank_error",          1, "failed"),
            (PAYMENT_C, CUSTOMER_C, "pay_demo_case_c", Decimal("4000"), "netbanking",  "card_declined",       3, "failed"),
            (PAYMENT_D, CUSTOMER_D, "pay_demo_case_d", Decimal("15000"),"card",        "do_not_honour",       1, "failed"),
            (PAYMENT_E, CUSTOMER_E, "pay_demo_case_e", Decimal("3000"), "upi",         "network_timeout",     1, "failed"),
        ]
        for pid, cid, ext_id, amt, method, fail_code, attempt, status in payments:
            await conn.execute("""
                INSERT INTO payments (id, merchant_id, customer_id, external_payment_id,
                    amount, currency, method, failure_code, attempt_number, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (external_payment_id) DO NOTHING
            """, pid, MERCHANT_ID, cid, ext_id, amt, "INR", method, fail_code, attempt, status)

        # ── Recovery Cases ────────────────────────────────────────────────────
        logger.info("Seeding demo recovery cases…")
        cases = [
            # (case_id, payment_id, customer_id, status, revenue_at_risk, notes)
            (CASE_A, PAYMENT_A, CUSTOMER_A, "DECISION_READY", Decimal("3000"),
             "retry_later", "not_required"),
            (CASE_B, PAYMENT_B, CUSTOMER_B, "DECISION_READY", Decimal("80"),
             "do_nothing", "not_required"),
            (CASE_C, PAYMENT_C, CUSTOMER_C, "DECISION_READY", Decimal("4000"),
             "reminder", "not_required"),
            (CASE_D, PAYMENT_D, CUSTOMER_D, "PENDING_APPROVAL", Decimal("15000"),
             "incentive", "pending"),
            (CASE_E, PAYMENT_E, CUSTOMER_E, "DECISION_READY", Decimal("3000"),
             "retry_now", "not_required"),
        ]
        for case_id, payment_id, customer_id, status, rar, selected_action, approval_status in cases:
            await conn.execute("""
                INSERT INTO recovery_cases (
                    id, merchant_id, customer_id, payment_id,
                    status, revenue_at_risk, selected_action, approval_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
            """,
                case_id, MERCHANT_ID, customer_id, payment_id,
                status, rar, selected_action, approval_status,
            )

        # ── Webhook dedup row for Case E (demo idempotency) ──────────────────
        logger.info("Seeding demo webhook event (Case E dedup demo)…")
        await conn.execute("""
            INSERT INTO webhook_events (
                event_id, payment_id, event_type, processing_status, raw_payload
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (event_id) DO NOTHING
        """,
            WEBHOOK_EVENT_E,
            "pay_demo_case_e",
            "payment.failed",
            "processed",
            '{"id": "demo-webhook-evt-00000000000000001", "entity": "event", "event": "payment.failed"}',
        )

        # ── Audit events for seeded cases ─────────────────────────────────────
        logger.info("Seeding audit events…")
        audit_events = [
            (CASE_A, "payment_failed",           "webhook",   "system"),
            (CASE_A, "context_loaded",           "pipeline",  "recoveryos"),
            (CASE_A, "predictions_generated",    "pipeline",  "recoveryos"),
            (CASE_A, "optimization_completed",   "pipeline",  "recoveryos"),
            (CASE_A, "guardrail_passed",         "pipeline",  "recoveryos"),
            (CASE_B, "payment_failed",           "webhook",   "system"),
            (CASE_B, "optimization_completed",   "pipeline",  "recoveryos"),
            (CASE_D, "payment_failed",           "webhook",   "system"),
            (CASE_D, "approval_requested",       "pipeline",  "recoveryos"),
        ]
        for case_id, event_type, source, actor in audit_events:
            await conn.execute("""
                INSERT INTO audit_logs (id, case_id, event_type, source, actor, input_snapshot, output_snapshot)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
            """,
                str(uuid.uuid4()), case_id, event_type, source, actor, "{}", "{}",
            )

    logger.info(
        "\n✓ Demo data seeded successfully.\n"
        "  5 demo cases:\n"
        "    A = %s  (DECISION_READY  — retry_later)\n"
        "    B = %s  (DECISION_READY  — do_nothing, ₹80)\n"
        "    C = %s  (DECISION_READY  — reminder, attempt #3)\n"
        "    D = %s  (PENDING_APPROVAL — incentive, ₹15,000)\n"
        "    E = %s  (DECISION_READY  — dedup demo)\n",
        CASE_A, CASE_B, CASE_C, CASE_D, CASE_E,
    )


if __name__ == "__main__":
    asyncio.run(seed())
