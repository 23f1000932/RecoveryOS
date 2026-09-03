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
    Launch a simulator experiment in the background.
    Returns experiment_id immediately.
    Results available via GET /api/simulator/{experiment_id}.
    """
    import uuid
    experiment_id = str(uuid.uuid4())
    logger.info(
        "Simulator run requested: rows=%d seed=%d → experiment_id=%s",
        body.rows, body.seed, experiment_id,
    )
    background_tasks.add_task(
        _run_experiment_background,
        experiment_id,
        body.rows,
        body.seed,
    )
    return SimulatorRunResponse(
        experiment_id=experiment_id,
        message=f"Experiment {experiment_id[:8]} started. Poll GET /api/simulator/{experiment_id} for results.",
    )


async def _run_experiment_background(
    experiment_id: str,
    rows: int,
    seed: int,
) -> None:
    """
    Background task: run the full A/B simulation and persist results.

    Architecture Rule 3: same RecoveryPipeline as webhook and dashboard.
    """
    import asyncio
    from datetime import datetime, timezone
    from decimal import Decimal
    import uuid as _uuid

    try:
        from ml.generate_data import generate_dataset
        from backend.db.repositories.experiments import ExperimentsRepository
        from backend.domain.models import ExperimentMetrics, ExperimentCase
        from backend.domain.enums import ActionType
        from backend.orchestrator.recovery_pipeline import create_pipeline
        from backend.orchestrator.context import CaseContext, RecoveryPolicy
        from backend.domain.enums import ExecutionMode, PipelineSource

        logger.info("Experiment %s: generating %d rows seed=%d", experiment_id, rows, seed)
        df = generate_dataset(rows=rows, seed=seed)
        logger.info("Experiment %s: dataset ready, running baseline + AI", experiment_id)

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

        pipeline = create_pipeline(execution_mode=ExecutionMode.SIMULATION)

        baseline_total = Decimal("0")
        ai_total = Decimal("0")
        ai_cost_total = Decimal("0")
        guardrail_stops = 0
        escalations = 0
        do_nothing_count = 0
        experiment_cases: list[ExperimentCase] = []

        for _, row in df.iterrows():
            case_id = str(row.get("case_id", _uuid.uuid4()))

            # Build CaseContext from synthetic row
            context = CaseContext(
                case_id=case_id,
                payment_id=str(row.get("payment_id", _uuid.uuid4())),
                customer_id=str(row.get("customer_id", _uuid.uuid4())),
                merchant_id="00000000-0000-0000-0000-000000000001",
                amount=Decimal(str(row["amount"])),
                currency="INR",
                method=str(row["payment_method"]),
                failure_code=str(row["failure_code"]),
                attempt_number=int(row["attempt_number"]),
                customer_success_rate=float(row["customer_success_rate"]),
                customer_transaction_count=int(row["customer_transaction_count"]),
                customer_success_count=int(row.get("customer_success_count", 0)),
                customer_failure_count=int(row["customer_failure_count"]),
                customer_avg_amount=Decimal(str(row["customer_avg_amount"])),
                time_since_failure_hours=float(row.get("time_since_failure", 1.0)),
                hour_of_day=int(row.get("hour_of_day", 12)),
                day_of_week=int(row.get("day_of_week", 1)),
                previous_failure_count=int(row["customer_failure_count"]),
                policy=policy,
            )

            # ── Baseline: fixed retry policy ───────────────────────────────────
            # Architecture §11: retry once, then stop
            baseline_action = ActionType.RETRY_NOW
            # Bernoulli draw using latent prob for retry_now
            import random
            import numpy as np
            rng_seed = seed + hash(case_id) % 100000
            rng = np.random.default_rng(rng_seed)
            retry_prob = float(row.get("p_retry_now", row["customer_success_rate"]))
            baseline_success = bool(rng.random() < retry_prob)
            baseline_recovered = Decimal(str(row["amount"])) if baseline_success else Decimal("0")
            baseline_total += baseline_recovered

            # ── AI: RecoveryPipeline ───────────────────────────────────────────
            proposal = await pipeline.process_case(
                context,
                source=PipelineSource.SIMULATOR,
                execute=True,
            )

            ai_action = proposal.recommended_action
            ai_recovered = proposal.actual_recovered
            ai_cost = proposal.action_result.cost if proposal.action_result else Decimal("0")

            ai_total += ai_recovered
            ai_cost_total += ai_cost

            if ai_action == ActionType.DO_NOTHING:
                do_nothing_count += 1
            if proposal.guardrail_result.verdict in ("stop",):
                guardrail_stops += 1
            if proposal.guardrail_result.verdict == "escalate":
                escalations += 1

            experiment_cases.append(ExperimentCase(
                case_id=case_id,
                baseline_action=baseline_action,
                baseline_success=baseline_success,
                baseline_recovered=baseline_recovered,
                ai_action=ai_action,
                ai_success=bool(ai_recovered > 0),
                ai_recovered=ai_recovered,
                ai_cost=ai_cost,
            ))

        incremental = ai_total - baseline_total
        net_incremental = incremental - ai_cost_total
        baseline_rate = sum(1 for c in experiment_cases if c.baseline_success) / max(len(experiment_cases), 1)
        ai_rate = sum(1 for c in experiment_cases if c.ai_success) / max(len(experiment_cases), 1)

        metrics = ExperimentMetrics(
            experiment_id=experiment_id,
            seed=seed,
            dataset_size=len(experiment_cases),
            baseline_policy="fixed_retry_once",
            ai_policy="recoveryos_v1",
            baseline_recovered=baseline_total,
            ai_recovered=ai_total,
            baseline_cost=Decimal("0"),
            ai_cost=ai_cost_total,
            incremental_recovery=incremental,
            net_incremental_recovery=net_incremental,
            baseline_recovery_rate=baseline_rate,
            ai_recovery_rate=ai_rate,
            guardrail_stops=guardrail_stops,
            escalations=escalations,
            do_nothing_count=do_nothing_count,
            created_at=datetime.now(timezone.utc),
        )

        repo = ExperimentsRepository()
        from backend.db.connection import db_available
        if db_available():
            await repo.create_experiment(metrics)
            await repo.save_experiment_cases(experiment_id, experiment_cases[:500])  # cap at 500
            logger.info(
                "Experiment %s complete: baseline=%.2f ai=%.2f incremental=%.2f net=%.2f",
                experiment_id, float(baseline_total), float(ai_total),
                float(incremental), float(net_incremental),
            )
        else:
            logger.warning(
                "Experiment %s: DB unavailable — results not persisted (Rule 4).",
                experiment_id,
            )

    except Exception as exc:
        logger.error("Experiment %s failed: %s", experiment_id, exc, exc_info=True)



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
