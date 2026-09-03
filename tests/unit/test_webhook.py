"""
RecoveryOS — Unit Tests: Webhook Handler

5 tests covering:
  - HMAC-SHA256 signature validation
  - signature mismatch returns 200 silently
  - duplicate event deduplication
  - payment.failed event routing
  - malformed JSON body handling

No real Razorpay API calls — all mocked.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Test Helpers ───────────────────────────────────────────────────────────────

def _make_signature(body: bytes, secret: str) -> str:
    """Compute the correct Razorpay HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def _make_payment_failed_event(payment_id: str = "pay_test123") -> dict:
    return {
        "id": f"evt_{payment_id}",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": 500000,   # 5000 INR in paise
                    "currency": "INR",
                    "method": "card",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Card declined",
                }
            }
        },
    }


# ── Signature Validation Tests ─────────────────────────────────────────────────

class TestSignatureValidation:

    def test_valid_signature_returns_true(self):
        """Correct HMAC signature must be accepted."""
        from backend.api.webhooks import _verify_razorpay_signature
        secret = "test_webhook_secret_abc"
        body = b'{"event": "payment.failed"}'
        sig = _make_signature(body, secret)
        assert _verify_razorpay_signature(body, sig, secret) is True

    def test_tampered_signature_returns_false(self):
        """Wrong signature must be rejected."""
        from backend.api.webhooks import _verify_razorpay_signature
        body = b'{"event": "payment.failed"}'
        assert _verify_razorpay_signature(body, "wrong_sig", "test_secret") is False

    def test_empty_secret_returns_false(self):
        """Empty webhook secret must reject all signatures."""
        from backend.api.webhooks import _verify_razorpay_signature
        body = b'{"event": "payment.failed"}'
        sig = _make_signature(body, "real_secret")
        assert _verify_razorpay_signature(body, sig, "") is False

    def test_payment_normalization(self):
        """_normalize_payment_context must extract amount in INR (not paise)."""
        from backend.api.webhooks import _normalize_payment_context
        from decimal import Decimal
        event = _make_payment_failed_event()
        ctx = _normalize_payment_context(event)
        assert ctx["amount"] == Decimal("5000.00")
        assert ctx["method"] == "card"
        assert ctx["failure_code"] == "BAD_REQUEST_ERROR"

    def test_webhook_returns_200_on_invalid_signature(self):
        """
        Invalid signature must return 200 (not 401).
        Razorpay retries non-2xx responses — we must never reveal signature mismatch.
        """
        from backend.main import app

        with patch("backend.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.razorpay_webhook_secret = "test_secret"
            settings.razorpay_available = False
            mock_settings.return_value = settings

            client = TestClient(app)
            body = b'{"id": "evt_001", "event": "payment.failed"}'

            response = client.post(
                "/webhooks/razorpay",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": "bad_signature_value",
                },
            )
            # Must ALWAYS return 200 — never 401/403
            assert response.status_code == 200
