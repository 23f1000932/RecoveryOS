"""
RecoveryOS — Policies API

GET /api/policies
Returns current merchant recovery policy for display on the Policies page.
Policy values come from the YAML file — not from the LLM.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from backend.config import get_settings
from backend.domain.schemas import PolicyView

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=PolicyView)
async def get_policy() -> PolicyView:
    """Return the current active merchant recovery policy."""
    try:
        import yaml
        settings = get_settings()
        with open(settings.policy_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        def _fmt(v) -> str:
            return f"{Decimal(str(v)):.2f}"

        return PolicyView(
            version=str(raw.get("version", "1.0")),
            max_retries_per_customer=int(raw.get("max_retries_per_customer", 2)),
            max_messages_per_customer=int(raw.get("max_messages_per_customer", 2)),
            max_incentive_per_customer=_fmt(raw.get("max_incentive_per_customer", 100)),
            daily_incentive_pool=_fmt(raw.get("daily_incentive_pool", 5000)),
            high_value_threshold=_fmt(raw.get("high_value_threshold", 10000)),
            recovery_window_hours=int(raw.get("recovery_window_hours", 48)),
            min_expected_net_revenue=_fmt(raw.get("min_expected_net_revenue", 100)),
            min_model_confidence=float(raw.get("min_model_confidence", 0.65)),
            auto_action_probability=float(raw.get("auto_action_probability", 0.70)),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Policy file not found")
    except Exception as exc:
        logger.error("Policy load error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load policy")
