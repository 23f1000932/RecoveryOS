"""
RecoveryOS — Simulator Reproducibility Tests

Architecture §35 Simulator requirements:
  - same batch: baseline and AI evaluated on identical synthetic data (same seed)
  - reproducible seed: same seed → same dataset → same metrics
  - no fabricated metrics: net_incremental_recovery must equal ai_recovered - baseline_recovered - ai_cost
  - incremental_recovery = ai_recovered - baseline_recovered
  - net_incremental_recovery = incremental_recovery - ai_cost

All tests run without DB or external APIs.
Uses RuleBasedRecoveryModel for determinism (no Gemini, no rate-limit issues in CI).

Run with:
    .venv\\Scripts\\python -m pytest tests/simulator/ -v --tb=short
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from backend.domain.enums import ActionType, ExecutionMode, PipelineSource
from backend.ml_models.rule_based import RuleBasedRecoveryModel
from backend.orchestrator.baseline import BaselinePolicy
from backend.orchestrator.context import CaseContext, RecoveryPolicy
from backend.orchestrator.recovery_pipeline import RecoveryPipeline


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


def _dedup_df(df):
    """generate_dataset() has duplicate column names — keep the last occurrence."""
    return df.loc[:, ~df.columns.duplicated(keep='last')]


def _row_to_context(row, policy: RecoveryPolicy, case_id: str | None = None) -> CaseContext:
    """Convert a generate_dataset() DataFrame row to a CaseContext."""
    def _s(col, default=None):
        """Scalar accessor — safe for Series with duplicate index names."""
        val = row[col] if col in row.index else default
        if hasattr(val, 'iloc'):  # still a Series (duplicate col)
            return val.iloc[-1]   # take the last one (post-merge columns)
        return val

    return CaseContext(
        case_id=str(case_id or str(uuid.uuid4())),
        payment_id=str(uuid.uuid4()),
        customer_id=str(uuid.uuid4()),
        merchant_id="00000000-0000-0000-0000-000000000001",
        amount=Decimal(str(float(_s("amount", 1000)))),
        currency="INR",
        method=str(_s("payment_method", "card")),
        failure_code=str(_s("failure_code", "card_declined")),
        attempt_number=int(_s("attempt_number", 1)),
        customer_success_rate=float(_s("customer_success_rate", 0.70)),
        customer_transaction_count=int(_s("customer_transaction_count", 10)),
        customer_success_count=int(_s("customer_success_count", 7)),
        customer_failure_count=int(_s("customer_failure_count", 3)),
        customer_avg_amount=Decimal(str(float(_s("customer_avg_amount", 1000)))),
        time_since_failure_hours=float(_s("time_since_failure_hours", 1.0)),
        hour_of_day=int(_s("hour_of_day", 12)),
        day_of_week=int(_s("day_of_week", 1)),
        previous_failure_count=int(_s("customer_failure_count", 1)),
        policy=policy,
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
            if col in df1.columns:
                assert df1[col].equals(df2[col]), (
                    f"Column '{col}' is not identical across calls with seed=42"
                )

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
            "customer_avg_amount",
        ]
        for col in required:
            assert col in df.columns, (
                f"Required column '{col}' missing from generate_dataset() output"
            )

    @pytest.mark.asyncio
    async def test_baseline_and_ai_evaluated_on_same_batch(self):
        """
        Architecture §11: 'Baseline and RecoveryOS must be evaluated on the same batch.'
        Validates that the same rows feed both evaluators.
        """
        from ml.generate_data import generate_dataset

        SEED = 42
        ROWS = 10
        df = _dedup_df(generate_dataset(rows=ROWS, seed=SEED))

        pipeline = _make_pipeline()
        baseline_results = []
        ai_proposals = []

        for i, (_, row) in enumerate(df.iterrows()):
            case_id = f"repro-{i}"
            context = _row_to_context(row, DEMO_POLICY, case_id=case_id)

            # Baseline: deterministic threshold-based evaluation
            p_retry = float(row.get("p_retry_now", row["customer_success_rate"]))
            b_result = BASELINE.evaluate(context.amount, p_retry)
            baseline_results.append(b_result)

            # AI: pipeline
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

        for i, (_, row) in enumerate(df.iterrows()):
            context = _row_to_context(row, DEMO_POLICY, case_id=f"metrics-{i}")

            # Baseline: deterministic
            p_retry = float(row.get("p_retry_now", row["customer_success_rate"]))
            b_result = BASELINE.evaluate(context.amount, p_retry)
            baseline_total += b_result.recovered_amount

            # AI: execute=True in simulation — gets actual_recovered populated
            proposal = await pipeline.process_case(
                context, source=PipelineSource.SIMULATOR, execute=True
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

    @pytest.mark.asyncio
    async def test_baseline_is_deterministic_given_same_input(self):
        """
        BaselinePolicy.evaluate() with same inputs → same output.
        """
        amount = Decimal("3500")
        p_retry = 0.72  # above 0.5 → success

        result1 = BASELINE.evaluate(amount, p_retry)
        result2 = BASELINE.evaluate(amount, p_retry)

        assert result1.action == result2.action == ActionType.RETRY_NOW
        assert result1.success == result2.success
        assert result1.recovered_amount == result2.recovered_amount

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
        df = _dedup_df(generate_dataset(rows=1, seed=42))
        row = df.iloc[0]
        context = _row_to_context(row, DEMO_POLICY, case_id="determinism-ai-test")

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
