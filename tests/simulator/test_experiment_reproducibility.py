"""
RecoveryOS — Experiment Loop Reproducibility & Counterfactual Correctness

These tests exercise `simulator.experiment.run_experiment` — the loop that
produces the project's north-star number (§2, net incremental recovery).

They exist because the loop previously lived inside a FastAPI background task,
so nothing could call it, and three compounding defects survived 130 passing
tests:

  1. per-row RNG seeded with `hash(case_id)` — Python salts str hashes per
     process, so the same seed gave different numbers every run;
  2. the verification adapter drawing from the unseeded global `random`;
  3. `latent_probability` never threaded into `verifier.verify()`, so the AI
     was scored against `customer_success_rate` instead of `p_<chosen_action>` —
     which made the optimizer's choice of action have *no effect* on simulated
     recovery, bypassing ACTION_LIFTS entirely.

Test 1 below catches (1) and (2). Test 2 catches (3). Test 3 checks the
monotone coupling that only holds when both arms share one uniform draw
(architecture §10.3).

No DB, no Gemini, no network.

Run with:
    .venv\\Scripts\\python -m pytest tests/simulator/test_experiment_reproducibility.py -v
"""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.domain.simulation import SimulationOutcome, derive_uniform_draw
from backend.ml_models.protocol import ActionPrediction
from backend.orchestrator.recovery_pipeline import RecoveryPipeline
from simulator.experiment import build_context, run_experiment

ROWS = 200
SEED = 42

# Metrics that must be byte-identical across runs. `experiment_id` and
# `created_at` are deliberately excluded — they are per-invocation identity, not
# measurement.
_VOLATILE_FIELDS = {"experiment_id", "created_at"}


class TestExperimentReproducibility:

    @pytest.mark.asyncio
    async def test_same_seed_produces_identical_metrics(self):
        """
        run_experiment(rows=N, seed=S) twice → every measured field identical.

        This is the determinism contract in simulator/experiment.py's docstring.
        Any unseeded randomness anywhere in the 10-stage pipeline breaks it.
        """
        first = await run_experiment(rows=ROWS, seed=SEED)
        second = await run_experiment(rows=ROWS, seed=SEED)

        measured = [f.name for f in fields(first.metrics) if f.name not in _VOLATILE_FIELDS]
        assert measured, "ExperimentMetrics has no measured fields — check the dataclass"

        differences = {
            name: (getattr(first.metrics, name), getattr(second.metrics, name))
            for name in measured
            if getattr(first.metrics, name) != getattr(second.metrics, name)
        }
        assert differences == {}, (
            f"Experiment is not reproducible with seed={SEED}. Differing fields: "
            f"{differences}"
        )

    @pytest.mark.asyncio
    async def test_same_seed_produces_identical_per_case_outcomes(self):
        """
        Reproducibility must hold case by case, not just in aggregate — two runs
        could coincidentally sum to the same total from different outcomes.
        """
        first = await run_experiment(rows=50, seed=SEED)
        second = await run_experiment(rows=50, seed=SEED)

        assert len(first.cases) == len(second.cases) == 50

        for i, (a, b) in enumerate(zip(first.cases, second.cases)):
            assert a == b, f"Case {i} differs between runs:\n  {a}\n  {b}"

    @pytest.mark.asyncio
    async def test_different_seeds_produce_different_metrics(self):
        """
        A determinism bug can also be faked by returning a constant. Different
        seeds must move the numbers.
        """
        a = await run_experiment(rows=ROWS, seed=42)
        b = await run_experiment(rows=ROWS, seed=99)

        assert a.metrics.ai_recovered != b.metrics.ai_recovered, (
            "Seeds 42 and 99 produced identical AI recovery — the seed is being ignored"
        )

    @pytest.mark.asyncio
    async def test_metric_identity_holds_on_real_output(self):
        """
        §35 anti-fabrication: the published aggregates must be arithmetic
        consequences of the per-case rows, not independently computed numbers.
        """
        output = await run_experiment(rows=100, seed=SEED)
        m = output.metrics

        assert m.baseline_recovered == sum(
            (c.baseline_recovered for c in output.cases), Decimal("0")
        )
        assert m.ai_recovered == sum((c.ai_recovered for c in output.cases), Decimal("0"))
        assert m.ai_cost == sum((c.ai_cost for c in output.cases), Decimal("0"))
        assert m.incremental_recovery == m.ai_recovered - m.baseline_recovered
        assert m.net_incremental_recovery == m.incremental_recovery - m.ai_cost
        assert m.baseline_cost == Decimal("0"), "Baseline spends nothing (§16)"

        n = len(output.cases)
        assert m.baseline_recovery_rate == sum(c.baseline_success for c in output.cases) / n
        assert m.ai_recovery_rate == sum(c.ai_success for c in output.cases) / n


class _AlwaysIncentiveModel:
    """
    Test double: names `incentive` the highest-probability action by a wide
    margin, so the EV optimizer selects it regardless of amount.
    """

    def predict_action_outcomes(self, context, actions) -> list[ActionPrediction]:
        return [
            ActionPrediction(
                action=action,
                probability=0.95 if action == ActionType.INCENTIVE else 0.05,
                confidence=0.99,
                model_name="test_always_incentive",
                model_version="0.0.0",
            )
            for action in actions
        ]


class TestVerificationUsesChosenAction:
    """
    The regression guard for defect (3). Because the AI was verified against
    `customer_success_rate`, the pipeline's entire optimization stage was
    decorative in the simulator: choosing `incentive` over `do_nothing` changed
    the cost but not the revenue.
    """

    @pytest.mark.asyncio
    async def test_recovery_resolves_against_p_of_selected_action(self):
        """
        Construct a case where the two candidate probabilities disagree about the
        outcome for one shared draw:

            p_incentive              = 0.90  → u=0.50 recovers
            customer_success_rate    = 0.10  → u=0.50 does not

        The pipeline selects `incentive`. If verification reads the chosen
        action's probability, the case recovers. If it falls back to
        `customer_success_rate` (the old behaviour), it does not.
        """
        from ml.generate_data import generate_dataset
        from backend.orchestrator.policy_loader import load_recovery_policy

        row = generate_dataset(rows=1, seed=SEED).iloc[0].copy()
        row["amount"] = 8000.0            # large enough that incentive clears min ENR
        row["customer_success_rate"] = 0.10
        row["attempt_number"] = 1
        context = build_context(row, load_recovery_policy())

        outcome = SimulationOutcome(
            latent_probabilities={
                ActionType.RETRY_NOW: 0.10,
                ActionType.RETRY_LATER: 0.10,
                ActionType.REMINDER: 0.10,
                ActionType.INCENTIVE: 0.90,
                ActionType.ESCALATE: 0.10,
                ActionType.DO_NOTHING: 0.05,
            },
            uniform_draw=0.50,
        )

        pipeline = RecoveryPipeline(
            model=_AlwaysIncentiveModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=None,
        )
        proposal = await pipeline.process_case(
            context, source=PipelineSource.SIMULATOR, execute=True, outcome=outcome,
        )

        assert proposal.recommended_action == ActionType.INCENTIVE, (
            "Test precondition failed: the optimizer did not select incentive, so "
            f"this case cannot distinguish the two probabilities (got "
            f"{proposal.recommended_action}, verdict={proposal.guardrail_result.verdict})"
        )
        assert proposal.actual_recovered > 0, (
            "Case was not recovered. With u=0.50 and p_incentive=0.90 it must be. "
            "Verification is resolving against customer_success_rate (0.10) instead "
            "of the probability of the action actually chosen."
        )

    @pytest.mark.asyncio
    async def test_unfavourable_draw_still_fails_the_chosen_action(self):
        """
        Symmetric guard: the fix must not turn verification into 'always recover'.
        Same case, draw above p_incentive → no recovery.
        """
        from ml.generate_data import generate_dataset
        from backend.orchestrator.policy_loader import load_recovery_policy

        row = generate_dataset(rows=1, seed=SEED).iloc[0].copy()
        row["amount"] = 8000.0
        row["customer_success_rate"] = 0.10
        row["attempt_number"] = 1
        context = build_context(row, load_recovery_policy())

        outcome = SimulationOutcome(
            latent_probabilities={a: 0.90 if a == ActionType.INCENTIVE else 0.10
                                  for a in ActionType},
            uniform_draw=0.95,
        )

        pipeline = RecoveryPipeline(
            model=_AlwaysIncentiveModel(),
            execution_mode=ExecutionMode.SIMULATION,
            agent=None,
        )
        proposal = await pipeline.process_case(
            context, source=PipelineSource.SIMULATOR, execute=True, outcome=outcome,
        )

        assert proposal.recommended_action == ActionType.INCENTIVE
        assert proposal.actual_recovered == Decimal("0"), (
            "u=0.95 exceeds every latent probability — nothing should recover"
        )


class TestSharedOutcomeEnvironment:
    """
    architecture §10.3: 'Baseline and AI must consume the same potential-outcome
    environment.' Concretely: one uniform draw per case, both arms comparing it
    against their own action's probability.
    """

    def test_uniform_draw_is_stable_across_processes(self):
        """
        The draw depends only on (seed, row_index) — no process-local state.
        derive_uniform_draw is what replaced hash(case_id).
        """
        for row_index in [0, 1, 7, 199]:
            repeated = {derive_uniform_draw(seed=SEED, row_index=row_index) for _ in range(5)}
            assert len(repeated) == 1, f"Draw is not stable for row {row_index}"

        distinct = {derive_uniform_draw(seed=SEED, row_index=i) for i in range(50)}
        assert len(distinct) == 50, "Rows are sharing draws — streams are not independent"

    def test_both_arms_read_one_draw_per_case(self):
        """
        A case's outcome for every action resolves against the same u. This is
        what makes the AI-minus-baseline difference a paired comparison rather
        than two independent samples.
        """
        from ml.generate_data import generate_dataset

        df = generate_dataset(rows=20, seed=SEED)
        for row_index, (_, row) in enumerate(df.iterrows()):
            outcome = SimulationOutcome.from_row(row, row_index=row_index, seed=SEED)
            expected = derive_uniform_draw(seed=SEED, row_index=row_index)
            assert outcome.uniform_draw == expected
            for action in ActionType:
                assert outcome.realized(action) == (
                    expected < outcome.probability_for(action)
                )

    @pytest.mark.asyncio
    async def test_ai_never_loses_a_case_it_had_better_odds_on(self):
        """
        Monotone coupling — the property that only holds under a shared draw.

        For any case where the baseline recovered (u < p_retry_now) and the AI
        chose an action with p_action >= p_retry_now, the AI must have recovered
        it too: u < p_retry_now <= p_action. Under independent draws this fails
        on roughly half of such cases, and the reported lift is mostly sampling
        noise rather than decision quality.
        """
        from ml.generate_data import generate_dataset

        output = await run_experiment(rows=ROWS, seed=SEED)
        df = generate_dataset(rows=ROWS, seed=SEED)

        outcomes = {
            str(row["case_id"]): SimulationOutcome.from_row(row, row_index=i, seed=SEED)
            for i, (_, row) in enumerate(df.iterrows())
        }
        assert len(outcomes) == ROWS, "Dataset has duplicate case_ids"

        compared = 0
        for case in output.cases:
            outcome = outcomes[case.case_id]
            p_baseline = outcome.probability_for(ActionType.RETRY_NOW)
            p_ai = outcome.probability_for(case.ai_action)

            if not case.baseline_success or p_ai < p_baseline:
                continue
            compared += 1
            assert case.ai_success, (
                f"Case {case.case_id}: baseline recovered at p={p_baseline:.3f} and "
                f"the AI chose {case.ai_action.value} at the higher p={p_ai:.3f}, yet "
                f"the AI did not recover it (u={outcome.uniform_draw:.3f}). The two "
                "arms are drawing from different streams."
            )
            assert case.ai_recovered == case.baseline_recovered, (
                "Both arms recovered the same case, so both must book the same "
                "gross amount — cost is tracked separately."
            )

        assert compared > 25, (
            f"Only {compared} of {ROWS} cases exercised the coupling property — "
            "too few to be a meaningful regression guard."
        )
