"""
RecoveryOS — Simulation Potential Outcomes

Implements the counterfactual outcome environment required by
architecture_v2.md §10.3:

    "Baseline and AI must consume the same potential-outcome environment.
     Do not independently sample a fresh random outcome every time
     baseline and AI are evaluated."

Method: common random numbers (CRN).

    For each case we derive ONE uniform draw u ∈ [0, 1) deterministically
    from (seed, row_index). The potential outcome for any action a is then

        Y(a) = 1[ u < p_a ]

    where p_a is that action's pre-baked latent probability from the
    synthetic dataset (ml/outcome_generator.py).

    Baseline evaluates Y(retry_now). RecoveryOS evaluates Y(chosen_action).
    Both read the same u, so:

      - the comparison is a true counterfactual on one shared world;
      - if p_chosen > p_retry_now the AI wins on *every* case where the
        draw falls between them, and never loses — the measured lift is
        the probability gain, not sampling noise;
      - the same seed always reproduces the same experiment.

Why not a fixed 0.5 threshold (the previous BaselinePolicy behaviour):
    success = (p >= 0.5) is deterministic but biased. A case with p=0.49
    would count as a guaranteed failure and p=0.51 as a guaranteed success,
    so aggregate recovery rate measures "fraction of cases above 0.5"
    rather than expected recovery. It also compresses the AI's advantage
    into the narrow band where p_baseline < 0.5 <= p_chosen.

Why not a fresh RNG per evaluation:
    Independent draws for baseline and AI put the two arms in different
    worlds. Any measured difference then mixes the policy effect with
    sampling noise, which is exactly what §10.3 forbids.

This module is pure computation — no I/O, no DB, no global state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.domain.enums import ActionType


def derive_uniform_draw(seed: int, row_index: int) -> float:
    """
    Derive the shared uniform draw for one case, deterministically.

    Args:
        seed:      The experiment's global seed.
        row_index: 0-based position of the case in the generated dataset.

    Returns:
        A float in [0, 1). Same (seed, row_index) always returns the same value,
        in any process, on any platform.

    Implementation note:
        `default_rng([seed, row_index])` spawns from a SeedSequence built on the
        pair, giving statistically independent streams per row.

        Deliberately NOT `default_rng(seed + row_index * 31337)` — that is the
        exact formula ml/outcome_generator.py:144 uses to generate this row's
        latent probabilities, so reusing it would draw the outcome from the same
        stream that produced the noise term baked into those probabilities,
        correlating the coin flip with the thing it is supposed to test.

        Also deliberately NOT seeded from case_id: Python salts str hashes per
        process (PYTHONHASHSEED), so hash(case_id) is not stable across runs.
    """
    return float(np.random.default_rng([seed, row_index]).random())


@dataclass(frozen=True)
class SimulationOutcome:
    """
    The pre-baked latent potential outcomes for a single case.

    latent_probabilities: p_a for every action, from the synthetic dataset.
    uniform_draw:         the one shared draw u used by every arm.
    """

    latent_probabilities: dict[ActionType, float]
    uniform_draw: float

    def probability_for(self, action: ActionType) -> float:
        """
        Latent probability of recovery for `action`.

        Raises KeyError if the action has no latent probability — that means the
        dataset and ActionType enum have drifted apart, which must fail loudly
        rather than silently substituting a different number.
        """
        return self.latent_probabilities[action]

    def realized(self, action: ActionType) -> bool:
        """
        Whether the payment is recovered under `action` in this world.

        Y(a) = 1[u < p_a] — the same u for every action, so outcomes across
        actions are coupled rather than independent.
        """
        return self.uniform_draw < self.probability_for(action)

    @classmethod
    def from_row(cls, row, row_index: int, seed: int) -> "SimulationOutcome":
        """
        Build the outcome environment for one generated dataset row.

        Args:
            row:       A pandas Series from ml.generate_data.generate_dataset().
                       Must carry a p_<action> column for every ActionType.
            row_index: 0-based position of the row in the dataset.
            seed:      The experiment's global seed.

        Reads the `p_<action.value>` columns declared in
        ml/features.py::PROBABILITY_COLUMNS.
        """
        probabilities = {
            action: float(row[f"p_{action.value}"])
            for action in ActionType
        }
        return cls(
            latent_probabilities=probabilities,
            uniform_draw=derive_uniform_draw(seed=seed, row_index=row_index),
        )
