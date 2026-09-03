"""Live scoring service — loads XGBoost model and produces risk scores."""

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Feature columns used by the model
FEATURE_COLS = [
    "total_orders", "total_refunds", "total_amount",
    "avg_amount", "max_amount", "refund_rate",
    "refund_ratio", "high_amount",
]

# Risk label thresholds
LABEL_THRESHOLDS = [
    (0.2, "allow"),
    (0.4, "monitor"),
    (0.6, "step_up_verification"),
    (0.8, "manual_review"),
    (1.0, "hold_for_review"),
]


class ScoringService:
    """Loads trained model and scores feature vectors."""

    def __init__(self, model_dir: str = "ml/artifacts"):
        self.model = None
        self.model_dir = Path(model_dir)
        self._load_model()

    def _load_model(self):
        """Load the trained XGBoost model."""
        try:
            import joblib
            model_path = self.model_dir / "model.pkl"
            if model_path.exists():
                self.model = joblib.load(model_path)
                logger.info("Model loaded from %s", model_path)
            else:
                logger.warning("Model not found at %s — using rule-based scoring", model_path)
        except Exception as e:
            logger.warning("Failed to load model: %s — using rule-based scoring", e)

    def score(self, features: dict[str, Any]) -> dict[str, Any]:
        """Score a feature vector and return risk assessment."""
        if self.model is not None:
            return self._ml_score(features)
        return self._rule_based_score(features)

    def _ml_score(self, features: dict[str, Any]) -> dict[str, Any]:
        """Score using the trained XGBoost model."""
        X = np.array([[features.get(col, 0) for col in FEATURE_COLS]])
        proba = self.model.predict_proba(X)[0][1]
        risk_score = float(proba)
        risk_label = self._get_label(risk_score)

        return {
            "risk_score": risk_score,
            "risk_label": risk_label,
            "model_version": "v5.0",
            "scoring_method": "xgboost",
            "shap_contributions": self._get_shap_contributions(X),
        }

    def _rule_based_score(self, features: dict[str, Any]) -> dict[str, Any]:
        """Fallback rule-based scoring when model is unavailable."""
        score = 0.0
        risk_factors = []

        refund_rate = features.get("refund_rate", 0)
        if refund_rate > 0.5:
            score += 0.3
            risk_factors.append("high_refund_rate")

        total_refunds = features.get("total_refunds", 0)
        if total_refunds > 3:
            score += 0.2
            risk_factors.append("multiple_refunds")

        max_amount = features.get("max_amount", 0)
        if max_amount > 100000:
            score += 0.2
            risk_factors.append("high_amount")

        if features.get("high_amount", 0):
            score += 0.1

        risk_score = min(score, 1.0)
        return {
            "risk_score": risk_score,
            "risk_label": self._get_label(risk_score),
            "model_version": "v5.0",
            "scoring_method": "rule_based",
            "risk_factors": risk_factors,
            "shap_contributions": [],
        }

    def _get_label(self, proba: float) -> str:
        """Convert probability to risk label."""
        for threshold, label in LABEL_THRESHOLDS:
            if proba < threshold:
                return label
        return "hold_for_review"

    def _get_shap_contributions(self, X: np.ndarray) -> list[dict]:
        """Get SHAP feature contributions if available."""
        try:
            import shap
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X)[0]
            contributions = []
            for col, val in zip(FEATURE_COLS, shap_values):
                contributions.append({
                    "feature": col,
                    "contribution": float(val),
                })
            contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
            return contributions[:5]
        except Exception:
            return []


# Global instance
_scoring_service = None


def get_scoring_service() -> ScoringService:
    """Get or create the global scoring service instance."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service
