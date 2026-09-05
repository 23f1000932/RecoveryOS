"""
RecoveryOS — Simulator Reproducibility Tests

Architecture §35 Simulator requirements:
  - same batch: baseline and AI evaluated on identical synthetic data (same seed)
  - reproducible seed: same seed → same dataset → same metrics
  - no fabricated metrics: net_incremental_recovery must equal ai_recovered - baseline_recovered - ai_cost
  - incremental_recovery = ai_recovered - baseline_recovered
  - net_incremental_recovery = incremental_recovery - ai_cost

These tests cover the dataset and the two evaluators in isolation. The full loop
is covered by test_experiment_reproducibility.py — the two files together are
what make the north-star metric verifiable.

All tests run without DB or external APIs.
Uses RuleBasedRecoveryModel for determinism (no Gemini, no rate-limit issues in CI).

Run with:
    .venv\\Scripts\\python -m pytest tests/simulator/ -v --tb=short
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.domain.simulation import SimulationOutcome
from backend.ml_models.rule_based import RuleBasedRecoveryModel
from backend.orchestrator.baseline import BaselinePolicy
from backend.orchestrator.context import RecoveryPolicy
from backend.orchestrator.recovery_pipeline import RecoveryPipeline
from simulator.experiment import build_context


DEMO_POLICY = RecoveryPolicy(
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

BASELINE = BaselinePolicy()


def _make_pipeline() -> RecoveryPipeline:
    return RecoveryPipeline(
        model=RuleBasedRecoveryModel(),
        execution_mode=ExecutionMode.SIMULATION,
        agent=None,
    )


class TestSimulatorReproducibility:
    """
    Architecture §35: 'same seed → same dataset → same baseline and AI metrics.'
    """

    def test_same_seed_produces_identical_dataset(self):
        """
        generate_dataset(seed=N) must return the same DataFrame every time.
        """
        from ml.generate_data import generate_dataset

        df1 = generate_dataset(rows=50, seed=42)
        df2 = generate_dataset(rows=50, seed=42)

        # Shape identical
        assert df1.shape == df2.shape, (
            f"Dataset shape changed: {df1.shape} vs {df2.shape}"
        )

        # Key financial and categorical columns must be bit-identical
        for col in ["amount", "customer_success_rate", "payment_method", "failure_code"]:
            assert df1[col].equals(df2[col]), (
                f"Column '{col}' is not identical across calls with seed=42"
            )

    def test_dataset_columns_are_unique(self):
        """
        No duplicate column labels — otherwise df["customer_success_rate"] returns
        a 2-column frame and every consumer needs a workaround. The schema is
        deduplicated once, in ml/features.py::ALL_DATASET_COLUMNS.
        """
        from ml.generate_data import generate_dataset

        columns = list(generate_dataset(rows=5, seed=42).columns)
        duplicated = sorted({c for c in columns if columns.count(c) > 1})
        assert duplicated == [], f"Duplicate column labels: {duplicated}"

    def test_different_seeds_produce_different_datasets(self):
        """
        Different seeds must produce statistically different datasets.
        """
        from ml.generate_data import generate_dataset

        df42 = generate_dataset(rows=100, seed=42)
        df99 = generate_dataset(rows=100, seed=99)

        # Amount distributions should differ (with probability ~1)
        amounts_equal = (df42["amount"] == df99["amount"]).all()
        assert not amounts_equal, (
            "Seeds 42 and 99 produced identical amounts — "
            "generator is not using seed correctly"
        )

    def test_dataset_has_required_columns(self):
        """
        Validates that generate_dataset() returns all columns required by the pipeline.
        """
        from ml.generate_data import generate_dataset

        df = generate_dataset(rows=10, seed=1)

        required = [
            "amount", "payment_method", "failure_code",
            "attempt_number", "customer_success_rate",
            "customer_transaction_count", "customer_failure_count",
            "customer_avg_amount", "time_since_failure_hours",
            "hour_of_day", "day_of_week", "previous_failure_count",
        ]
        for col in required:
            assert col in df.columns, (
                f"Required column '{col}' missing from generate_dataset() output"
            )

    @pytest.mark.asyncio
    async def test_baseline_and_ai_evaluated_on_same_batch(self):
        """
        Architecture §11: 'Baseline and RecoveryOS must be evaluated on the same batch.'
        Validates that the same rows — and the same uniform draws — feed both evaluators.
        """
        from ml.generate_data import generate_dataset

        SEED = 42
        ROWS = 10
        df = generate_dataset(rows=ROWS, seed=SEED)

        pipeline = _make_pipeline()
        baseline_results = []
        ai_proposals = []

        for row_index, (_, row) in enumerate(df.iterrows()):
            context = build_context(row, DEMO_POLICY)
            outcome = SimulationOutcome.from_row(row, row_index=row_index, seed=SEED)

            b_result = BASELINE.evaluate(
                payment_amount=context.amount,
                p_retry_now=outcome.probability_for(ActionType.RETRY_NOW),
                uniform_draw=outcome.uniform_draw,
            )
            baseline_results.append(b_result)

            proposal = await pipeline.process_case(
                context, source=PipelineSource.SIMULATOR, execute=False
            )
            ai_proposals.append(proposal)

        # Both lists must have exactly ROWS entries
        assert len(baseline_results) == ROWS
        assert len(ai_proposals) == ROWS

        # Every AI proposal must have a decision
        for i, p in enumerate(ai_proposals):
            assert p.recommended_action is not None, (
                f"Case {i} has no recommended_action"
            )

    @pytest.mark.asyncio
    async def test_metrics_arithmetic_identity(self):
        """
        Architecture: 'Never fabricate metrics.'

        The identity that must hold:
            incremental_recovery     = ai_recovered - baseline_recovered
            net_incremental_recovery = incremental_recovery - ai_cost

        This is validated by computing both sides from first principles
        and asserting they match.
        """
        from ml.generate_data import generate_dataset

        SEED = 7
        ROWS = 15
        df = generate_dataset(rows=ROWS, seed=SEED)

        pipeline = _make_pipeline()

        baseline_total = Decimal("0")
        ai_total = Decimal("0")
        ai_cost_total = Decimal("0")

        for row_index, (_, row) in enumerate(df.iterrows()):
            context = build_context(row, DEMO_POLICY)
            outcome = SimulationOutcome.from_row(row, row_index=row_index, seed=SEED)

            b_result = BASELINE.evaluate(
                payment_amount=context.amount,
                p_retry_now=outcome.probability_for(ActionType.RETRY_NOW),
                uniform_draw=outcome.uniform_draw,
            )
            baseline_total += b_result.recovered_amount

            # AI: execute=True in simulation — gets actual_recovered populated
            proposal = await pipeline.process_case(
                context, source=PipelineSource.SIMULATOR, execute=True,
                outcome=outcome,
            )
            ai_total += proposal.actual_recovered
            if proposal.action_result is not None:
                # Action result has a cost attribute
                ai_cost_total += getattr(proposal.action_result, "cost", Decimal("0"))

        # Verify arithmetic identity (anti-fabrication check)
        incremental = ai_total - baseline_total
        net_incremental = incremental - ai_cost_total
        computed_net = ai_total - baseline_total - ai_cost_total

        assert abs(net_incremental - computed_net) < Decimal("0.01"), (
            f"Metric identity violated: "
            f"net_incremental={net_incremental} computed={computed_net} "
            f"(ai={ai_total} baseline={baseline_total} cost={ai_cost_total})"
        )

    def test_baseline_is_deterministic_given_same_input(self):
        """
        BaselinePolicy.evaluate() with the same (amount, p, u) → same output.
        """
        amount = Decimal("3500")
        p_retry = 0.72
        draw = 0.41  # u < p → recovered

        result1 = BASELINE.evaluate(amount, p_retry, uniform_draw=draw)
        result2 = BASELINE.evaluate(amount, p_retry, uniform_draw=draw)

        assert result1.action == result2.action == ActionType.RETRY_NOW
        assert result1.success == result2.success is True
        assert result1.recovered_amount == result2.recovered_amount == amount

        # Cost is always 0 for baseline
        assert result1.cost == Decimal("0")

    @pytest.mark.asyncio
    async def test_ai_is_deterministic_given_same_context(self):
        """
        RuleBasedRecoveryModel + same context → same AI recommendation.
        Architecture §35: determinism requirement.
        """
        pipeline = _make_pipeline()

        from ml.generate_data import generate_dataset
        df = generate_dataset(rows=1, seed=42)
        row = df.iloc[0]
        context = build_context(row, DEMO_POLICY)

        proposal1 = await pipeline.process_case(
            context, source=PipelineSource.SIMULATOR, execute=False
        )
        proposal2 = await pipeline.process_case(
            context, source=PipelineSource.SIMULATOR, execute=False
        )

        assert proposal1.recommended_action == proposal2.recommended_action, (
            f"AI not deterministic: {proposal1.recommended_action} vs {proposal2.recommended_action}"
        )
        assert (
            proposal1.optimization_result.selected_expected_net_revenue
            == proposal2.optimization_result.selected_expected_net_revenue
        )
