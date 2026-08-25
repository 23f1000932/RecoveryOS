"""
RecoveryOS — Simulator API

POST /api/simulator/run
GET  /api/simulator/{experiment_id}
GET  /api/simulator/             (list recent experiments)
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.domain.schemas import SimulatorResult, SimulatorRunRequest, SimulatorRunResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.post("/run", response_model=SimulatorRunResponse)
async def run_simulation(
    body: SimulatorRunRequest,
    background_tasks: BackgroundTasks,
) -> SimulatorRunResponse:
    """
    Launch a simulator experiment.
    Runs Baseline and RecoveryOS on the same seeded synthetic dataset.
    Returns experiment_id immediately. Results available via GET /api/simulator/{id}.
    Wired to ExperimentRunner in Phase 8.
    """
    import uuid
    experiment_id = str(uuid.uuid4())
    logger.info(
        "Simulator run requested: rows=%d seed=%d → experiment_id=%s",
        body.rows, body.seed, experiment_id,
    )
    # Phase 1 stub — full simulator wired in Phase 8
    return SimulatorRunResponse(
        experiment_id=experiment_id,
        message="Simulator will be fully wired in Phase 8. Experiment ID reserved.",
    )


@router.get("/{experiment_id}", response_model=SimulatorResult)
async def get_experiment(experiment_id: str) -> SimulatorResult:
    """
    Retrieve experiment results.
    Wired to experiments repository in Phase 8.
    """
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
        cases=cases,
        created_at=experiment["created_at"],
    )
