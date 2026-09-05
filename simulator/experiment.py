"""
RecoveryOS — Simulator Experiment Runner

Runs one A/B experiment: the fixed-retry baseline against the full RecoveryOS
pipeline, over the same synthetic dataset, in the same potential-outcome
environment.

architecture_v2.md §15 / techstack.md §15:

        Synthetic Dataset
              ↓
        Baseline Policy ──────────┐
                                  ├──→ Same experiment environment
        RecoveryOS Policy ────────┘
              ↓
        Business Metrics

This lives outside backend/api/ on purpose (techstack §22: "do not put the
decision logic directly inside the route"). It previously lived inside the
route's background task, which is why three separate reproducibility defects
sat undetected through 130 passing tests — nothing could call the loop.

Determinism contract:
    run_experiment(rows=N, seed=S) returns byte-identical metrics on every
    call, in every process. The only inputs are N and S. Everything random is
    derived from S via backend.domain.simulation.derive_uniform_draw.

    The Gemini agent is deliberately not part of that contract — it only ever
    writes explanation prose, never the action or the money, so its
    non-determinism cannot move a metric. See below.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.domain.models import ExperimentCase, ExperimentMetrics
from backend.domain.simulation import SimulationOutcome
from backend.orchestrator.baseline import BaselinePolicy
from backend.orchestrator.context import CaseContext
from backend.orchestrator.policy_loader import load_recovery_policy
from backend.orchestrator.recovery_pipeline import create_pipeline

logger = logging.getLogger(__name__)

# Namespace for deriving stable payment IDs from case IDs. The generated dataset
# has no payment_id column; the previous code called uuid4() per row, so the same
# seed produced different payment IDs every run.
_PAYMENT_NAMESPACE = uuid.UUID("6f2a1d64-0b3e-4c8a-9d21-8e5f0c7b4a19")

# Single-merchant demo deployment.
_MERCHANT_ID = "00000000-0000-0000-0000-000000000001"

# Cap on per-case rows persisted alongside the aggregate metrics. The aggregate
# always covers the full dataset; only the inspectable sample is truncated.
MAX_PERSISTED_CASES = 500


@dataclass(frozen=True)
class ExperimentOutput:
    """Everything one experiment produced: aggregates plus per-case detail."""

    metrics: ExperimentMetrics
    cases: list[ExperimentCase]


def _payment_id_for(case_id: str) -> str:
    """Derive a stable payment_id from a case_id (uuid5 — same input, same output)."""
    return f"pay_{uuid.uuid5(_PAYMENT_NAMESPACE, case_id).hex[:14]}"


def build_context(row, policy) -> CaseContext:
    """
    Map one generated dataset row onto a CaseContext.

    Every one of the 13 trained features in ml/features.py::FEATURE_COLUMNS must
    be carried across verbatim. Reading a column that does not exist and quietly
    defaulting it creates train/serve skew: the model learned on the real
    distribution but scores against a constant.
    """
    case_id = str(row["case_id"])
    return CaseContext(
        case_id=case_id,
        payment_id=_payment_id_for(case_id),
        customer_id=str(row["customer_id"]),
        merchant_id=_MERCHANT_ID,
        amount=Decimal(str(row["amount"])),
        currency="INR",
        method=str(row["payment_method"]),
        failure_code=str(row["failure_code"]),
        attempt_number=int(row["attempt_number"]),
        customer_success_rate=float(row["customer_success_rate"]),
        customer_transaction_count=int(row["customer_transaction_count"]),
        customer_success_count=int(row["customer_success_count"]),
        customer_failure_count=int(row["customer_failure_count"]),
        customer_avg_amount=Decimal(str(row["customer_avg_amount"])),
        time_since_failure_hours=float(row["time_since_failure_hours"]),
        hour_of_day=int(row["hour_of_day"]),
        day_of_week=int(row["day_of_week"]),
        previous_failure_count=int(row["previous_failure_count"]),
        policy=policy,
    )


async def run_experiment(
    rows: int,
    seed: int,
    experiment_id: str | None = None,
) -> ExperimentOutput:
    """
    Run one baseline-vs-RecoveryOS experiment over `rows` synthetic cases.

    Args:
        rows:          Number of synthetic cases to generate.
        seed:          Global seed. Fully determines the experiment.
        experiment_id: Optional caller-supplied ID (the API allocates one up
                       front so it can return immediately). Generated if None.

    Returns:
        ExperimentOutput — aggregate metrics plus per-case detail.

    Does no I/O beyond generating the dataset: persistence is the caller's job,
    matching the pipeline's own "caller owns DB writes" contract.

    Architecture Rule 3: uses the same RecoveryPipeline as the webhook and the
    dashboard. Only the event source and execution adapter differ.
    """
    from ml.generate_data import generate_dataset

    experiment_id = experiment_id or str(uuid.uuid4())

    logger.info("Experiment %s: generating %d rows seed=%d", experiment_id, rows, seed)
    df = generate_dataset(rows=rows, seed=seed)

    policy = load_recovery_policy()
    baseline = BaselinePolicy()
    pipeline = create_pipeline(execution_mode=ExecutionMode.SIMULATION)

    logger.info("Experiment %s: dataset ready, running baseline + AI", experiment_id)

    baseline_total = Decimal("0")
    ai_total = Decimal("0")
    ai_cost_total = Decimal("0")
    guardrail_stops = 0
    escalations = 0
    do_nothing_count = 0
    approvals_required = 0
    cases: list[ExperimentCase] = []

    # Positional index, not the DataFrame's label — the shared draw must be keyed
    # to position so it is stable regardless of index type.
    for row_index, (_, row) in enumerate(df.iterrows()):
        context = build_context(row, policy)

        # The case's potential outcomes: p per action, plus the one uniform draw
        # both arms resolve against (§10.3).
        outcome = SimulationOutcome.from_row(row, row_index=row_index, seed=seed)

        # ── Baseline: fixed retry once (§11, §16) ─────────────────────────────
        baseline_result = baseline.evaluate(
            payment_amount=context.amount,
            p_retry_now=outcome.probability_for(ActionType.RETRY_NOW),
            uniform_draw=outcome.uniform_draw,
        )
        baseline_total += baseline_result.recovered_amount

        # ── RecoveryOS: full pipeline, scored on the action it chose ──────────
        # approved=True models the merchant granting the approvals the guardrail
        # engine asks for. A batch experiment has no human, so the alternative is
        # to score every high-value case as ₹0 recovered while the baseline
        # retries it freely — which measures an unstaffed approval queue, not the
        # quality of the policy's decisions. On seed=42/200 rows that single
        # effect moves the headline by ~₹130k, because the 10 cases above the
        # ₹10,000 approval threshold hold 21.7% of all the money at risk.
        # The operational load is reported separately as approvals_required.
        proposal = await pipeline.process_case(
            context,
            source=PipelineSource.SIMULATOR,
            approved=True,
            execute=True,
            outcome=outcome,
        )

        ai_action = proposal.recommended_action
        ai_recovered = proposal.actual_recovered
        ai_cost = proposal.action_result.cost if proposal.action_result else Decimal("0")

        ai_total += ai_recovered
        ai_cost_total += ai_cost

        if ai_action == ActionType.DO_NOTHING:
            do_nothing_count += 1
        if proposal.guardrail_result.verdict == "stop":
            guardrail_stops += 1
        if proposal.guardrail_result.verdict == "escalate":
            escalations += 1
        if proposal.requires_approval:
            approvals_required += 1

        cases.append(ExperimentCase(
            case_id=context.case_id,
            baseline_action=baseline_result.action,
            baseline_success=baseline_result.success,
            baseline_recovered=baseline_result.recovered_amount,
            ai_action=ai_action,
            ai_success=bool(ai_recovered > 0),
            ai_recovered=ai_recovered,
            ai_cost=ai_cost,
        ))

    n = max(len(cases), 1)
    incremental = ai_total - baseline_total
    net_incremental = incremental - ai_cost_total

    metrics = ExperimentMetrics(
        experiment_id=experiment_id,
        seed=seed,
        dataset_size=len(cases),
        baseline_policy="fixed_retry_once",
        ai_policy="recoveryos_v1",
        baseline_recovered=baseline_total,
        ai_recovered=ai_total,
        baseline_cost=Decimal("0"),
        ai_cost=ai_cost_total,
        incremental_recovery=incremental,
        net_incremental_recovery=net_incremental,
        baseline_recovery_rate=sum(1 for c in cases if c.baseline_success) / n,
        ai_recovery_rate=sum(1 for c in cases if c.ai_success) / n,
        guardrail_stops=guardrail_stops,
        escalations=escalations,
        do_nothing_count=do_nothing_count,
        approvals_required=approvals_required,
        created_at=datetime.now(timezone.utc),
    )

    logger.info(
        "Experiment %s complete: baseline=%.2f ai=%.2f incremental=%.2f net=%.2f "
        "baseline_rate=%.3f ai_rate=%.3f approvals_required=%d",
        experiment_id, float(baseline_total), float(ai_total),
        float(incremental), float(net_incremental),
        metrics.baseline_recovery_rate, metrics.ai_recovery_rate,
        approvals_required,
    )

    return ExperimentOutput(metrics=metrics, cases=cases)


async def run_and_persist(rows: int, seed: int, experiment_id: str) -> None:
    """
    Run an experiment and store it. Entry point for the API background task.

    Never raises: a failed experiment must not take down the worker. The error
    is logged and the experiment simply never appears (the GET returns 404).
    """
    try:
        output = await run_experiment(rows=rows, seed=seed, experiment_id=experiment_id)
    except Exception as exc:
        logger.error("Experiment %s failed: %s", experiment_id, exc, exc_info=True)
        return

    try:
        from backend.db.connection import db_available
        from backend.db.repositories.experiments import ExperimentsRepository

        if not db_available():
            logger.warning(
                "Experiment %s: DB unavailable — results not persisted (Rule 4).",
                experiment_id,
            )
            return

        repo = ExperimentsRepository()
        await repo.create_experiment(output.metrics)
        await repo.save_experiment_cases(
            experiment_id, output.cases[:MAX_PERSISTED_CASES]
        )
        logger.info("Experiment %s persisted (%d cases stored, %d total).",
                    experiment_id,
                    min(len(output.cases), MAX_PERSISTED_CASES),
                    len(output.cases))
    except Exception as exc:
        logger.error(
            "Experiment %s: computed successfully but persistence failed: %s",
            experiment_id, exc, exc_info=True,
        )
