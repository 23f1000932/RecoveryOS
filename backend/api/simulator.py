"""
RecoveryOS — Simulator API

POST /api/simulator/run
GET  /api/simulator/{experiment_id}

The experiment itself lives in simulator/experiment.py (techstack §22: no
decision logic in the route).
"""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.domain.schemas import SimulatorResult, SimulatorRunRequest, SimulatorRunResponse
from simulator.experiment import run_and_persist

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.post("/run", response_model=SimulatorRunResponse)
async def run_simulation(
    body: SimulatorRunRequest,
    background_tasks: BackgroundTasks,
) -> SimulatorRunResponse:
    """
    Launch a simulator experiment in the background.
    Returns experiment_id immediately.
    Results available via GET /api/simulator/{experiment_id}.
    """
    experiment_id = str(uuid.uuid4())
    logger.info(
        "Simulator run requested: rows=%d seed=%d → experiment_id=%s",
        body.rows, body.seed, experiment_id,
    )
    background_tasks.add_task(
        run_and_persist,
        rows=body.rows,
        seed=body.seed,
        experiment_id=experiment_id,
    )
    return SimulatorRunResponse(
        experiment_id=experiment_id,
        message=(
            f"Experiment {experiment_id[:8]} started. "
            f"Poll GET /api/simulator/{experiment_id} for results."
        ),
    )


@router.get("/{experiment_id}", response_model=SimulatorResult)
async def get_experiment(experiment_id: str) -> SimulatorResult:
    """Retrieve experiment results."""
    from backend.db.repositories.experiments import ExperimentsRepository
    repo = ExperimentsRepository()
    experiment = await repo.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    cases_data = await repo.get_experiment_cases(experiment_id, limit=200)

    from backend.domain.schemas import SimulatorCaseResult
    from backend.domain.enums import ActionType
    from decimal import Decimal

    def _fmt(v) -> str:
        return f"{Decimal(str(v or 0)):.2f}"

    cases = [
        SimulatorCaseResult(
            case_id=str(c["case_id"]),
            baseline_action=ActionType(c["baseline_action"]),
            baseline_success=c["baseline_success"],
            baseline_recovered=_fmt(c["baseline_recovered"]),
            ai_action=ActionType(c["ai_action"]),
            ai_success=c["ai_success"],
            ai_recovered=_fmt(c["ai_recovered"]),
            ai_cost=_fmt(c["ai_cost"]),
        )
        for c in cases_data
    ]

    return SimulatorResult(
        experiment_id=str(experiment["id"]),
        seed=experiment["seed"],
        dataset_size=experiment["dataset_size"],
        baseline_policy=experiment["baseline_policy"],
        ai_policy=experiment["ai_policy"],
        baseline_recovered=_fmt(experiment["baseline_recovered"]),
        ai_recovered=_fmt(experiment["ai_recovered"]),
        baseline_cost=_fmt(experiment["baseline_cost"]),
        ai_cost=_fmt(experiment["ai_cost"]),
        incremental_recovery=_fmt(experiment["incremental_recovery"]),
        net_incremental_recovery=_fmt(experiment["net_incremental_recovery"]),
        baseline_recovery_rate=float(experiment["baseline_recovery_rate"]),
        ai_recovery_rate=float(experiment["ai_recovery_rate"]),
        guardrail_stops=experiment["guardrail_stops"],
        escalations=experiment["escalations"],
        do_nothing_count=experiment["do_nothing_count"],
        approvals_required=experiment["approvals_required"],
        cases=cases,
        created_at=experiment["created_at"],
    )
