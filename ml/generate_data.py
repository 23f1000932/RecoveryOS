"""
RecoveryOS — Synthetic Dataset Generator

Public API:
    generate_dataset(rows=10_000, seed=42) → pd.DataFrame

This produces the single authoritative dataset for Phase 2+.
The same seed guarantees the same latent potential outcomes —
which means Baseline and RecoveryOS are evaluated counterfactually.

Design principles:
  - One function, deterministic given (rows, seed).
  - Customer-first: generate customers, then attach failed payments.
  - Outcome-last: latent probabilities stamped in final step.
  - Realistic INR distributions (Razorpay context).
  - No DB I/O, no API calls.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import (
    FEATURE_COLUMNS,
    PROBABILITY_COLUMNS,
    encode_failure_code,
    encode_method,
)
from ml.outcome_generator import generate_case_outcomes

# ── Constants ─────────────────────────────────────────────────────────────────

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]
METHOD_PROBS    = [0.45,   0.35, 0.15,         0.05  ]

FAILURE_CODES = [
    "insufficient_funds", "card_declined", "bank_error",
    "network_timeout",    "do_not_honour", "unknown",
]
FAILURE_PROBS = [0.30, 0.25, 0.15, 0.10, 0.10, 0.10]


# ── Customer Generator ─────────────────────────────────────────────────────────

def _generate_customers(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate n synthetic customers.

    Distributions are calibrated to resemble realistic Indian e-commerce:
      - Most customers have 5–30 transactions.
      - Success rate biased toward 0.80 (Beta(8,2)).
      - Average amounts follow a log-normal centred on ₹3,000.
    """
    # Transaction counts: negative binomial → right-skewed integers
    # n_nb=5, p=0.25 gives mean ≈ 15, reasonably long tail
    tx_counts = rng.negative_binomial(n=5, p=0.25, size=n)
    tx_counts = np.clip(tx_counts, 1, 200).astype(int)

    # Success rate per customer
    success_rates = rng.beta(a=8, b=2, size=n)  # mean ≈ 0.80

    # Derive success/failure counts from the rate
    success_counts = (tx_counts * success_rates).astype(int)
    failure_counts = tx_counts - success_counts

    # Average amount: LogNormal centred on ₹3,000
    avg_amounts = rng.lognormal(mean=np.log(3000), sigma=0.8, size=n)
    avg_amounts = np.clip(avg_amounts, 100, 500_000)

    # Preferred method
    preferred_methods = rng.choice(PAYMENT_METHODS, size=n, p=METHOD_PROBS)

    customer_ids = [str(uuid.uuid4()) for _ in range(n)]

    return pd.DataFrame({
        "customer_id":                customer_ids,
        "customer_transaction_count": tx_counts,
        "customer_success_count":     success_counts,
        "customer_failure_count":     failure_counts,
        "customer_success_rate":      success_rates.round(4),
        "customer_avg_amount":        avg_amounts.round(2),
        "preferred_method":           preferred_methods,
    })


# ── Payment Generator ──────────────────────────────────────────────────────────

def _generate_payments(
    customers: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Generate one failed payment per customer row.

    Each payment uses the customer's avg_amount as the LogNormal mean,
    with ±20% log-space noise to produce realistic variance.
    """
    n = len(customers)

    # Amount: LogNormal around each customer's avg_amount
    # sigma=0.2 gives ≈ ±20% variation
    log_means = np.log(customers["customer_avg_amount"].values)
    amounts = rng.lognormal(mean=log_means, sigma=0.2)
    amounts = np.clip(amounts, 10, 500_000).round(2)

    # Payment method: some use preferred, some switch
    # 70% use preferred method, 30% switch to another
    use_preferred = rng.random(n) < 0.70
    random_methods = rng.choice(PAYMENT_METHODS, size=n, p=METHOD_PROBS)
    payment_methods = np.where(
        use_preferred,
        customers["preferred_method"].values,
        random_methods,
    )

    # Failure codes
    failure_codes = rng.choice(FAILURE_CODES, size=n, p=FAILURE_PROBS)

    # Attempt numbers: heavily weighted toward first attempt
    attempt_numbers = rng.choice([1, 2, 3, 4], size=n, p=[0.70, 0.20, 0.08, 0.02])

    # Time since failure: uniform 0.5–12 hours
    time_since_failure = rng.uniform(0.5, 12.0, size=n).round(2)

    # Hour of day: bimodal — business hours (9–12) and evening (18–22)
    morning = rng.integers(9, 13, size=n)
    evening = rng.integers(18, 23, size=n)
    is_morning = rng.random(n) < 0.45
    hour_of_day = np.where(is_morning, morning, evening).astype(int)

    # Day of week: weekdays more common than weekends
    day_weights = [0.18, 0.17, 0.17, 0.17, 0.16, 0.08, 0.07]  # Mon–Sun
    day_of_week = rng.choice(range(7), size=n, p=day_weights)

    # Previous failure count: derived from customer failure history
    previous_failure_count = customers["customer_failure_count"].values

    return pd.DataFrame({
        "amount":                    amounts,
        "payment_method":            payment_methods,
        "failure_code":              failure_codes,
        "attempt_number":            attempt_numbers,
        "time_since_failure_hours":  time_since_failure,
        "hour_of_day":               hour_of_day.astype(int),
        "day_of_week":               day_of_week.astype(int),
        "previous_failure_count":    previous_failure_count.astype(int),
    })


# ── Main Generator ─────────────────────────────────────────────────────────────

def generate_dataset(rows: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic dataset of failed payment recovery cases.

    Args:
        rows: Number of cases to generate (10–50,000 recommended).
        seed: Global random seed. Same seed → identical DataFrame.

    Returns:
        pd.DataFrame with all feature columns + latent probability columns.
        Columns: case_id, customer_id, [customer features],
                 [13 ML features], [6 p_* outcome columns],
                 payment_method, failure_code.

    Note:
        The p_* columns are the ground-truth latent outcomes.
        Both Baseline and RecoveryOS consume these — never re-sample.
    """
    if rows < 1:
        raise ValueError(f"rows must be >= 1, got {rows}")

    rng = np.random.default_rng(seed=seed)

    # Step 1: Generate customers
    customers = _generate_customers(rows, rng)

    # Step 2: Generate payments for those customers
    payments = _generate_payments(customers, rng)

    # Step 3: Combine into a working DataFrame
    df = pd.concat([customers, payments], axis=1)

    # Step 4: Encode categorical features to integers
    df["method_encoded"] = df["payment_method"].map(
        lambda m: encode_method(m)
    )
    df["failure_code_encoded"] = df["failure_code"].map(
        lambda c: encode_failure_code(c)
    )

    # Step 5: Add case IDs (deterministic from seed — two int64 halves → 128-bit UUID)
    case_rng = np.random.default_rng(seed=seed + 999_999)
    case_ids: list[str] = []
    for _ in range(rows):
        high = int(case_rng.integers(0, 2**63, dtype=np.int64))
        low  = int(case_rng.integers(0, 2**63, dtype=np.int64))
        case_ids.append(str(uuid.UUID(int=(high << 64) | low)))
    df.insert(0, "case_id", case_ids)

    # Step 6: Generate latent potential outcomes (the counterfactual core)
    outcome_rows: list[dict[str, float]] = []
    for i, row in enumerate(df.itertuples(index=False)):
        outcomes = generate_case_outcomes(
            row_index=i,
            global_seed=seed,
            success_rate=float(row.customer_success_rate),
            transaction_count=int(row.customer_transaction_count),
            avg_amount=float(row.customer_avg_amount),
            failure_code_encoded=int(row.failure_code_encoded),
            attempt_number=int(row.attempt_number),
            amount=float(row.amount),
        )
        outcome_rows.append({
            "p_retry_now":   outcomes["retry_now"],
            "p_retry_later": outcomes["retry_later"],
            "p_reminder":    outcomes["reminder"],
            "p_incentive":   outcomes["incentive"],
            "p_escalate":    outcomes["escalate"],
            "p_do_nothing":  outcomes["do_nothing"],
        })

    outcomes_df = pd.DataFrame(outcome_rows)
    df = pd.concat([df.reset_index(drop=True), outcomes_df], axis=1)

    # Step 7: Enforce column ordering
    final_columns = (
        ["case_id", "customer_id"]
        + [
            "customer_transaction_count", "customer_success_count",
            "customer_failure_count", "customer_success_rate",
            "customer_avg_amount", "preferred_method",
        ]
        + FEATURE_COLUMNS
        + PROBABILITY_COLUMNS
        + ["payment_method", "failure_code"]
    )
    df = df[final_columns]

    return df.reset_index(drop=True)


def save_dataset(df: pd.DataFrame, seed: int) -> Path:
    """
    Save the dataset to ml/data/synthetic_{seed}.parquet for inspection.
    Creates the directory if it doesn't exist.
    Returns the path where the file was saved.
    """
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / f"synthetic_{seed}.parquet"
    df.to_parquet(path, index=False)
    return path
