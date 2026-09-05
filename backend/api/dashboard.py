"""
RecoveryOS — Dashboard API

GET /api/dashboard/summary
Returns aggregate financial metrics for the Command Center.
All financial values are computed by backend SQL — never by frontend.

Safe failure (Rule 4): when DATABASE_URL is not configured, returns
a zeroed-out summary rather than a 500. The UI renders zeros correctly.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter

from backend.db.connection import db_available
from backend.domain.schemas import DashboardSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


def _fmt(value: Decimal | float | int | None) -> str:
    """Format a numeric value as a plain decimal string (INR)."""
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)):.2f}"


def _zero_summary() -> DashboardSummary:
    """Return a zeroed-out DashboardSummary when DB is unavailable."""
    return DashboardSummary(
        revenue_at_risk="0.00",
        revenue_recovered="0.00",
        baseline_recovered="0.00",
        incremental_recovery="0.00",
        net_incremental_recovery="0.00",
        intervention_spend="0.00",
        recovery_rate=0.0,
        baseline_recovery_rate=0.0,
        guardrail_stops=0,
        escalations=0,
        do_nothing_count=0,
        total_cases=0,
        pending_approval_count=0,
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary() -> DashboardSummary:
    """
    Aggregate dashboard metrics.
    Revenue at Risk, Revenue Recovered, Baseline, Incremental, Net Incremental.

    Returns zeros when the database is not configured (development mode).
    """
    # Rule 4 — Safe failure: no DB → return zeros, not a 500
    if not db_available():
        logger.info("Dashboard summary: database not configured, returning zeros.")
        return _zero_summary()

    try:
        from backend.db.repositories.recovery_cases import RecoveryCaseRepository
        from backend.db.repositories.experiments import ExperimentsRepository

        repo = RecoveryCaseRepository()
        data = await repo.get_dashboard_summary(MERCHANT_ID)

        # Use latest experiment run as baseline comparison if available
        exp_repo = ExperimentsRepository()
        experiments = await exp_repo.list_experiments(limit=1)
        baseline_recovered = Decimal("0")
        if experiments:
            baseline_recovered = Decimal(str(experiments[0].get("baseline_recovered", 0)))

        revenue_recovered = Decimal(str(data.get("revenue_recovered", 0)))
        revenue_at_risk = Decimal(str(data.get("revenue_at_risk", 0)))
        intervention_spend = Decimal(str(data.get("intervention_spend", 0)))
        incremental = Decimal(str(data.get("incremental_recovery", 0)))
        net_incremental = Decimal(str(data.get("net_incremental_recovery", 0)))
        total = int(data.get("total_cases", 0))
        recovered_cases = int(data.get("recovered_cases", 0))

        recovery_rate = recovered_cases / total if total > 0 else 0.0
        baseline_rate = float(experiments[0].get("baseline_recovery_rate", 0.0)) if experiments else 0.0

        return DashboardSummary(
            revenue_at_risk=_fmt(revenue_at_risk),
            revenue_recovered=_fmt(revenue_recovered),
            baseline_recovered=_fmt(baseline_recovered),
            incremental_recovery=_fmt(incremental),
            net_incremental_recovery=_fmt(net_incremental),
            intervention_spend=_fmt(intervention_spend),
            recovery_rate=round(recovery_rate, 4),
            baseline_recovery_rate=round(baseline_rate, 4),
            guardrail_stops=int(data.get("guardrail_stops", 0)),
            escalations=int(data.get("escalations", 0)),
            do_nothing_count=int(data.get("do_nothing_count", 0)),
            total_cases=total,
            pending_approval_count=int(data.get("pending_approval_count", 0)),
        )

    except Exception as exc:
        logger.error("Dashboard summary error: %s", exc)
        # Return zeros rather than crashing — the UI will show empty state
        return _zero_summary()
