"""
RecoveryOS — Unit Tests: Synthetic Data Generator

5 test cases verifying:
  1. Reproducibility   — same seed → identical DataFrames
  2. Seed sensitivity  — different seeds → different outcomes
  3. Schema           — all expected columns present, zero NaN
  4. Probability bounds — all p_* columns in [0.0, 1.0]
  5. Action lift sanity — p_incentive > p_do_nothing for every row

These tests do NOT need a database or network.
They run in well under 1 second on 200-row datasets.
"""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from ml.generate_data import generate_dataset
from ml.features import FEATURE_COLUMNS, PROBABILITY_COLUMNS, ALL_DATASET_COLUMNS


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def df_seed42() -> pd.DataFrame:
    """A 200-row dataset with seed=42. Shared across tests."""
    return generate_dataset(rows=200, seed=42)


@pytest.fixture(scope="module")
def df_seed42_again() -> pd.DataFrame:
    """A second independent call with the same seed — for reproducibility test."""
    return generate_dataset(rows=200, seed=42)


@pytest.fixture(scope="module")
def df_seed99() -> pd.DataFrame:
    """A 200-row dataset with seed=99 — for seed sensitivity test."""
    return generate_dataset(rows=200, seed=99)


# ── Test 1: Reproducibility ────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_identical_dataframes(
        self,
        df_seed42: pd.DataFrame,
        df_seed42_again: pd.DataFrame,
    ) -> None:
        """
        Calling generate_dataset twice with the same seed must return
        exactly identical DataFrames.

        This guarantees counterfactual validity: Baseline and RecoveryOS
        consume the same latent outcomes when run with the same seed.
        """
        assert df_seed42.shape == df_seed42_again.shape, (
            "Shape mismatch between two identical seeds"
        )

        for col in PROBABILITY_COLUMNS:
            np.testing.assert_array_equal(
                df_seed42[col].values,
                df_seed42_again[col].values,
                err_msg=f"Column {col!r} differed between identical seeds",
            )

        for col in FEATURE_COLUMNS:
            np.testing.assert_array_equal(
                df_seed42[col].values,
                df_seed42_again[col].values,
                err_msg=f"Feature column {col!r} differed between identical seeds",
            )


# ── Test 2: Seed Sensitivity ───────────────────────────────────────────────────

class TestSeedSensitivity:
    def test_different_seeds_produce_different_data(
        self,
        df_seed42: pd.DataFrame,
        df_seed99: pd.DataFrame,
    ) -> None:
        """
        Two different seeds must produce meaningfully different data.
        Checks that p_retry_now values differ — if seeds produce identical
        data, the RNG seeding is broken.
        """
        # The probability arrays should NOT be equal
        are_equal = np.allclose(
            df_seed42["p_retry_now"].values,
            df_seed99["p_retry_now"].values,
            atol=1e-6,
        )
        assert not are_equal, (
            "p_retry_now is identical for seed=42 and seed=99 — RNG seeding is broken"
        )

    def test_amounts_differ_by_seed(
        self,
        df_seed42: pd.DataFrame,
        df_seed99: pd.DataFrame,
    ) -> None:
        """Amounts should differ between seeds."""
        are_equal = np.allclose(
            df_seed42["amount"].values,
            df_seed99["amount"].values,
            atol=0.01,
        )
        assert not are_equal, "Amounts are identical for different seeds — RNG broken"


# ── Test 3: Schema Completeness ────────────────────────────────────────────────

class TestSchemaCompleteness:
    def test_all_feature_columns_present(self, df_seed42: pd.DataFrame) -> None:
        """Every column in FEATURE_COLUMNS must be present in the DataFrame."""
        for col in FEATURE_COLUMNS:
            assert col in df_seed42.columns, (
                f"Feature column {col!r} is missing from the dataset"
            )

    def test_all_probability_columns_present(self, df_seed42: pd.DataFrame) -> None:
        """Every column in PROBABILITY_COLUMNS must be present."""
        for col in PROBABILITY_COLUMNS:
            assert col in df_seed42.columns, (
                f"Probability column {col!r} is missing from the dataset"
            )

    def test_required_id_columns_present(self, df_seed42: pd.DataFrame) -> None:
        """case_id and customer_id must be present."""
        assert "case_id" in df_seed42.columns
        assert "customer_id" in df_seed42.columns

    def test_no_null_values(self, df_seed42: pd.DataFrame) -> None:
        """The dataset must contain zero NaN/None values."""
        null_counts = df_seed42.isnull().sum()
        columns_with_nulls = null_counts[null_counts > 0]
        assert columns_with_nulls.empty, (
            f"Found NaN values in columns: {columns_with_nulls.to_dict()}"
        )

    def test_row_count_matches_requested(self) -> None:
        """generate_dataset(rows=N) must return exactly N rows."""
        for n in [10, 50, 200, 500]:
            df = generate_dataset(rows=n, seed=1)
            assert len(df) == n, (
                f"Expected {n} rows but got {len(df)}"
            )

    def test_raises_on_invalid_rows(self) -> None:
        """generate_dataset(rows=0) must raise ValueError."""
        with pytest.raises(ValueError):
            generate_dataset(rows=0, seed=42)


# ── Test 4: Probability Bounds ─────────────────────────────────────────────────

class TestProbabilityBounds:
    def test_all_probabilities_in_unit_interval(self, df_seed42: pd.DataFrame) -> None:
        """Every p_* column must contain values strictly in [0.0, 1.0]."""
        for col in PROBABILITY_COLUMNS:
            vals = df_seed42[col].values
            assert (vals >= 0.0).all(), (
                f"{col} contains values < 0.0: min={vals.min():.6f}"
            )
            assert (vals <= 1.0).all(), (
                f"{col} contains values > 1.0: max={vals.max():.6f}"
            )

    def test_probabilities_are_not_trivially_uniform(
        self, df_seed42: pd.DataFrame
    ) -> None:
        """
        Probabilities must not all be the same value — the model must produce
        meaningful variation across cases.
        """
        for col in PROBABILITY_COLUMNS:
            std = df_seed42[col].std()
            assert std > 0.01, (
                f"{col} has nearly zero variance (std={std:.6f}) — "
                "outcome generator is not varying with features"
            )


# ── Test 5: Action Lift Sanity ─────────────────────────────────────────────────

class TestActionLiftSanity:
    def test_incentive_always_beats_do_nothing(self, df_seed42: pd.DataFrame) -> None:
        """
        p_incentive must be greater than p_do_nothing for every single row.

        The incentive lift is +1.2 logits, do_nothing is -2.5 logits —
        a difference of 3.7 logits. No amount of per-row noise (clamped at ±0.5)
        should close this gap.
        """
        incentive = df_seed42["p_incentive"].values
        do_nothing = df_seed42["p_do_nothing"].values
        violations = (incentive <= do_nothing).sum()
        assert violations == 0, (
            f"{violations} rows where p_incentive <= p_do_nothing — "
            "action lift calibration is broken"
        )

    def test_retry_later_beats_retry_now_on_average(
        self, df_seed42: pd.DataFrame
    ) -> None:
        """
        On average, p_retry_later should exceed p_retry_now.
        retry_later lift is +0.8 vs retry_now +0.3 — should hold on average.
        """
        mean_later = df_seed42["p_retry_later"].mean()
        mean_now = df_seed42["p_retry_now"].mean()
        assert mean_later > mean_now, (
            f"Mean p_retry_later ({mean_later:.4f}) is not greater than "
            f"mean p_retry_now ({mean_now:.4f}) — lift calibration problem"
        )

    def test_do_nothing_lowest_on_average(self, df_seed42: pd.DataFrame) -> None:
        """
        On average, p_do_nothing should be lower than all other actions.
        Its lift is -2.5 logits, far below all others.
        """
        do_nothing_mean = df_seed42["p_do_nothing"].mean()
        for col in PROBABILITY_COLUMNS:
            if col == "p_do_nothing":
                continue
            other_mean = df_seed42[col].mean()
            assert do_nothing_mean < other_mean, (
                f"p_do_nothing mean ({do_nothing_mean:.4f}) is not less than "
                f"{col} mean ({other_mean:.4f})"
            )
