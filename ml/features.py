"""
RecoveryOS — Feature Schema

Authoritative definition of the 13 ML features used by:
  - outcome_generator.py (Phase 2 synthetic data)
  - RuleBasedRecoveryModel (Phase 3 baseline)
  - XGBoostRecoveryModel (Phase 4 ML training + inference)

Rules:
  - Never use post-action information as a feature.
  - Never let ML code re-define these columns independently.
  - Any schema change must be reflected here first, then in downstream code.
"""

from __future__ import annotations

# ── Payment Method Encoding ────────────────────────────────────────────────────
# card=0, upi=1, netbanking=2, wallet=3
METHOD_ENCODING: dict[str, int] = {
    "card": 0,
    "upi": 1,
    "netbanking": 2,
    "wallet": 3,
}

METHOD_DECODING: dict[int, str] = {v: k for k, v in METHOD_ENCODING.items()}

# ── Failure Code Encoding ──────────────────────────────────────────────────────
# 8 categories
FAILURE_CODE_ENCODING: dict[str, int] = {
    "insufficient_funds": 0,
    "card_declined": 1,
    "bank_error": 2,
    "network_timeout": 3,
    "do_not_honour": 4,
    "expired_card": 5,
    "cvv_mismatch": 6,
    "unknown": 7,
}

FAILURE_CODE_DECODING: dict[int, str] = {v: k for k, v in FAILURE_CODE_ENCODING.items()}

# ── Authoritative Feature Column List ─────────────────────────────────────────
# The XGBoost model is trained on exactly these columns, in this order.
# Do NOT change order without retraining.
FEATURE_COLUMNS: list[str] = [
    "amount",                       # float — payment amount (INR)
    "method_encoded",               # int   — payment method (see METHOD_ENCODING)
    "failure_code_encoded",         # int   — failure code (see FAILURE_CODE_ENCODING)
    "attempt_number",               # int   — 1–4
    "customer_transaction_count",   # int   — lifetime tx count
    "customer_success_count",       # int   — lifetime successful payments
    "customer_failure_count",       # int   — lifetime failed payments
    "customer_success_rate",        # float — success / total (0–1)
    "customer_avg_amount",          # float — customer lifetime avg amount
    "time_since_failure_hours",     # float — hours since the failure event
    "hour_of_day",                  # int   — 0–23
    "day_of_week",                  # int   — 0 (Mon)–6 (Sun)
    "previous_failure_count",       # int   — prior failures for this customer
]

# ── Outcome Probability Columns ────────────────────────────────────────────────
# One column per action — the latent ground-truth for the simulator.
PROBABILITY_COLUMNS: list[str] = [
    "p_retry_now",
    "p_retry_later",
    "p_reminder",
    "p_incentive",
    "p_escalate",
    "p_do_nothing",
]

# ── Helper Column Names (non-feature, kept for display / debug) ────────────────
HELPER_COLUMNS: list[str] = [
    "case_id",
    "customer_id",
    "payment_method",          # human-readable string
    "failure_code",            # human-readable string
    "preferred_method",        # customer's preferred method string
    "customer_transaction_count",
    "customer_success_count",
    "customer_failure_count",
    "customer_success_rate",
    "customer_avg_amount",
]

# ── All Columns in a Generated Dataset ────────────────────────────────────────
ALL_DATASET_COLUMNS: list[str] = (
    ["case_id", "customer_id"]
    + [
        "customer_transaction_count",
        "customer_success_count",
        "customer_failure_count",
        "customer_success_rate",
        "customer_avg_amount",
        "preferred_method",
    ]
    + FEATURE_COLUMNS
    + PROBABILITY_COLUMNS
    + ["payment_method", "failure_code"]
)


def encode_method(method: str) -> int:
    """Encode a payment method string to its integer representation.
    Returns 0 (card) for unknown methods.
    """
    return METHOD_ENCODING.get(method, 0)


def encode_failure_code(code: str) -> int:
    """Encode a failure code string to its integer representation.
    Returns 7 (unknown) for unrecognised codes.
    """
    return FAILURE_CODE_ENCODING.get(code, 7)


def decode_method(encoded: int) -> str:
    """Decode an integer back to a payment method string."""
    return METHOD_DECODING.get(encoded, "unknown")


def decode_failure_code(encoded: int) -> str:
    """Decode an integer back to a failure code string."""
    return FAILURE_CODE_DECODING.get(encoded, "unknown")
