"""
Model Evaluation
================

Loads a trained model and evaluates it on a held-out test set, producing
PR-AUC, confusion matrix, classification report, and a precision-recall
curve plot.

Usage::

    python -m backend.ml.evaluate \\
        --model-path ./artifacts/model.pkl \\
        --data-dir ./data \\
        --output-dir ./artifacts
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
)

logger = logging.getLogger(__name__)

# Must match the feature columns used during training
FEATURE_COLS = [
    "total_orders",
    "total_refunds",
    "total_amount",
    "avg_amount",
    "max_amount",
    "refund_rate",
    "refund_ratio",
    "high_amount",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_model(path: str | Path) -> Any:
    """Load a pickled model from *path*.

    Parameters
    ----------
    path : str or Path
        Path to a ``.pkl`` file.

    Returns
    -------
    model
        The deserialised scikit-learn / XGBoost model.
    """
    path = Path(path)
    logger.info("Loading model from %s", path)
    with open(path, "rb") as fh:
        model = pickle.load(fh)
    return model


def evaluate(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    output_dir: str | Path = "artifacts",
) -> Dict[str, Any]:
    """Evaluate *model* on the test set and persist results.

    Parameters
    ----------
    model : trained classifier
    X_test : pd.DataFrame
    y_test : pd.Series
    output_dir : str or Path
        Directory where ``evaluation_results.json`` and the PR-curve plot
        will be saved.

    Returns
    -------
    results : dict
        Keys: ``pr_auc``, ``confusion_matrix``, ``classification_report``,
        ``precision_recall_curve`` (path to saved plot).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    # Metrics
    pr_auc = float(average_precision_score(y_test, y_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()
    report = classification_report(y_test, y_pred, output_dict=True)

    logger.info("Test PR-AUC: %.4f", pr_auc)
    logger.info("Confusion matrix:\n%s", confusion_matrix(y_test, y_pred))
    logger.info(
        "Classification report:\n%s",
        classification_report(y_test, y_pred),
    )

    # --- Precision-Recall curve plot ---------------------------------------
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(recall, precision, color="steelblue", lw=2,
            label=f"XGBoost (PR-AUC = {pr_auc:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    pr_curve_path = out / "pr_curve.png"
    fig.savefig(pr_curve_path, dpi=150)
    plt.close(fig)
    logger.info("Saved PR curve to %s", pr_curve_path)

    # --- Persist results ---------------------------------------------------
    results: Dict[str, Any] = {
        "pr_auc": pr_auc,
        "confusion_matrix": cm,
        "classification_report": report,
        "pr_curve_path": str(pr_curve_path),
    }

    results_path = out / "evaluation_results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    logger.info("Saved evaluation_results.json to %s", results_path)

    return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run model evaluation on the test set."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard model evaluation"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="artifacts/model.pkl",
        help="Path to trained model .pkl (default: artifacts/model.pkl)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Directory containing events.json (default: data)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts",
        help="Directory for evaluation outputs (default: artifacts)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load model
    model = load_model(args.model_path)

    # Load test split (saved by train.py) or rebuild from events.json
    test_csv = Path(args.output_dir) / "test_split.csv"
    if test_csv.exists():
        logger.info("Loading pre-saved test split from %s", test_csv)
        test_df = pd.read_csv(test_csv)
    else:
        logger.info("No test_split.csv found; rebuilding splits from events.json")
        from backend.ml.train import create_splits, load_data

        df = load_data(args.data_dir)
        _, _, test_df = create_splits(df)

    X_test = test_df[FEATURE_COLS]
    y_test = test_df["label"]

    # Evaluate
    results = evaluate(model, X_test, y_test, output_dir=args.output_dir)

    logger.info("Evaluation complete -- PR-AUC: %.4f", results["pr_auc"])


if __name__ == "__main__":
    main()
