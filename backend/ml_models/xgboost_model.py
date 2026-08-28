"""
RecoveryOS — XGBoost Recovery Model

Trained XGBoost-based recovery outcome model.
Satisfies RecoveryOutcomeModel Protocol via duck typing.

Architecture rules (§9):
  - Loads one .joblib artifact per action at construction time.
  - predict_action_outcomes() is the only public method.
  - The optimizer must not know which model generated predictions.

Rule 4 — Safe failure:
  - If artifacts are missing, raises ModelNotTrainedError.
  - RecoveryPipeline catches this and falls back to RuleBasedRecoveryModel.

To train:
    .venv\\Scripts\\python -m ml.train --rows 50000 --seed 42
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import numpy as np

from backend.domain.enums import ActionType
from backend.ml_models.protocol import ActionPrediction

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext

logger = logging.getLogger(__name__)

MODEL_NAME = "xgboost_recovery"
MODEL_VERSION = "xgb_v1"
MODEL_ARTIFACT_DIR = Path("ml/models")

# Fixed confidence for Phase 4 — calibrated confidence is a Phase 4.5 enhancement
FIXED_CONFIDENCE = 0.85


class ModelNotTrainedError(RuntimeError):
    """
    Raised when XGBoost artifacts haven't been trained yet.

    Resolution: run `.venv\\Scripts\\python -m ml.train --rows 50000 --seed 42`
    """


class XGBoostRecoveryModel:
    """
    Trained XGBoost-based recovery outcome model.

    One XGBClassifier per ActionType, loaded from ml/models/<action>.joblib.
    Uses predict_proba()[:, 1] to get success probabilities.

    Thread-safe: models are read-only after construction.
    """

    def __init__(self, artifact_dir: Path = MODEL_ARTIFACT_DIR) -> None:
        """
        Load all 6 model artifacts from artifact_dir.

        Raises:
            ModelNotTrainedError: If any artifact is missing.
        """
        self._artifact_dir = artifact_dir
        self._models: dict[ActionType, object] = {}
        self._load_artifacts()
        logger.info(
            "XGBoostRecoveryModel loaded %d action models from %s",
            len(self._models), artifact_dir,
        )

    def _artifact_path(self, action: ActionType) -> Path:
        return self._artifact_dir / f"{action.value}.joblib"

    def _load_artifacts(self) -> None:
        """Load all 6 .joblib artifacts. Raises ModelNotTrainedError if any missing."""
        missing = []
        for action in ActionType:
            path = self._artifact_path(action)
            if not path.exists():
                missing.append(str(path))

        if missing:
            raise ModelNotTrainedError(
                f"XGBoost model artifacts not found: {missing}\n"
                "Run: .venv\\Scripts\\python -m ml.train --rows 50000 --seed 42"
            )

        for action in ActionType:
            self._models[action] = joblib.load(self._artifact_path(action))

    def predict_action_outcomes(
        self,
        context: CaseContext,
        actions: list[ActionType],
    ) -> list[ActionPrediction]:
        """
        Predict success probability for each requested action.

        Uses predict_proba()[:, 1] from the per-action XGBClassifier.
        Probabilities are clipped to (0.01, 0.99) for numerical stability.

        Returns one ActionPrediction per action, in input order.
        """
        from ml.training import context_to_feature_vector

        X = context_to_feature_vector(context)

        predictions: list[ActionPrediction] = []
        for action in actions:
            clf = self._models.get(action)
            if clf is None:
                logger.warning("No model for action %s — using 0.5 fallback.", action)
                probability = 0.5
            else:
                raw_prob = float(clf.predict_proba(X)[0, 1])
                probability = float(np.clip(raw_prob, 0.01, 0.99))

            predictions.append(
                ActionPrediction(
                    action=action,
                    probability=probability,
                    confidence=FIXED_CONFIDENCE,
                    model_name=MODEL_NAME,
                    model_version=MODEL_VERSION,
                )
            )

        return predictions
