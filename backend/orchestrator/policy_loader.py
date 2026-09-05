"""
RecoveryOS — Recovery Policy Loader

Single place that turns policies/recovery_policy.yaml into a RecoveryPolicy.

techstack.md §28:
    "The policy loader validates this configuration."

architecture_v2.md: the merchant policy in YAML is authoritative. Before this
module existed, backend/api/simulator.py and the case endpoints each hardcoded
their own copy of the policy numbers, so editing the YAML changed the Policies
page but not the decisions the pipeline actually made.

The result is cached: the policy is read once per process, not per case. The
pipeline never touches disk mid-run — the caller loads the policy and puts it
on the CaseContext.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from functools import lru_cache

from backend.orchestrator.context import RecoveryPolicy

logger = logging.getLogger(__name__)


# Fallback used only when the YAML is missing or unreadable (Rule 4 — safe
# failure: degrade to the documented defaults, never crash the process).
# These mirror policies/recovery_policy.yaml as committed.
_DEFAULTS: dict = {
    "version": "1.0",
    "max_retries_per_customer": 2,
    "max_messages_per_customer": 2,
    "max_incentive_per_customer": 100,
    "daily_incentive_pool": 5000,
    "high_value_threshold": 10000,
    "min_expected_net_revenue": 100,
    "min_model_confidence": 0.65,
    "recovery_window_hours": 48,
    "auto_action_probability": 0.70,
}


def _build(raw: dict) -> RecoveryPolicy:
    """Coerce a raw YAML mapping into a validated RecoveryPolicy."""

    def _dec(key: str) -> Decimal:
        # str() first: Decimal(float) would inherit binary float error into money.
        return Decimal(str(raw.get(key, _DEFAULTS[key])))

    def _int(key: str) -> int:
        return int(raw.get(key, _DEFAULTS[key]))

    def _float(key: str) -> float:
        return float(raw.get(key, _DEFAULTS[key]))

    policy = RecoveryPolicy(
        version=str(raw.get("version", _DEFAULTS["version"])),
        max_retries_per_customer=_int("max_retries_per_customer"),
        max_messages_per_customer=_int("max_messages_per_customer"),
        max_incentive_per_customer=_dec("max_incentive_per_customer"),
        daily_incentive_pool=_dec("daily_incentive_pool"),
        high_value_threshold=_dec("high_value_threshold"),
        min_expected_net_revenue=_dec("min_expected_net_revenue"),
        min_model_confidence=_float("min_model_confidence"),
        recovery_window_hours=_int("recovery_window_hours"),
        auto_action_probability=_float("auto_action_probability"),
    )

    # Validate the invariants the guardrail engine relies on. A malformed policy
    # must fail loudly here rather than silently permitting unbounded spend.
    if policy.max_incentive_per_customer < 0:
        raise ValueError("max_incentive_per_customer must not be negative")
    if policy.daily_incentive_pool < policy.max_incentive_per_customer:
        raise ValueError(
            "daily_incentive_pool must be >= max_incentive_per_customer "
            f"(got pool={policy.daily_incentive_pool}, "
            f"per_customer={policy.max_incentive_per_customer})"
        )
    if not 0.0 <= policy.min_model_confidence <= 1.0:
        raise ValueError("min_model_confidence must be in [0, 1]")
    if not 0.0 <= policy.auto_action_probability <= 1.0:
        raise ValueError("auto_action_probability must be in [0, 1]")
    if policy.recovery_window_hours <= 0:
        raise ValueError("recovery_window_hours must be positive")

    return policy


@lru_cache(maxsize=1)
def load_recovery_policy() -> RecoveryPolicy:
    """
    Load and validate the merchant recovery policy from YAML.

    Cached for the life of the process. Call load_recovery_policy.cache_clear()
    in tests that need to re-read a modified file.

    Falls back to the committed defaults if the file is missing or unparseable,
    logging a warning — a missing policy file must not take the API down.
    A file that parses but violates an invariant DOES raise: silently running
    with a nonsensical budget is worse than failing.
    """
    import yaml

    from backend.config import get_settings

    path = get_settings().policy_path
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError) as exc:
        logger.warning(
            "load_recovery_policy: could not read %s (%s). "
            "Using built-in defaults (Rule 4 — safe failure).",
            path, exc,
        )
        raw = {}

    policy = _build(raw)
    logger.info(
        "load_recovery_policy: version=%s max_incentive=%s pool=%s "
        "high_value=%s min_enr=%s min_confidence=%.2f",
        policy.version,
        policy.max_incentive_per_customer,
        policy.daily_incentive_pool,
        policy.high_value_threshold,
        policy.min_expected_net_revenue,
        policy.min_model_confidence,
    )
    return policy
