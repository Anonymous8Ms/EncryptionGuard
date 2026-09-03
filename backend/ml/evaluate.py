"""
EncryptionGuard ML Model Evaluation
====================================

Evaluate trained XGBoost model on test data with PR-AUC, confusion matrix,
classification report, and precision-recall curve visualization.

Usage:
    python -m backend.ml.evaluate --model-path backend/ml/artifacts/model.pkl \
        --data-dir data/ --output-dir backend/ml/artifacts/
"""

import argparse
import json
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
)

from ml.train import create_splits, load_data


def load_model(path: str) -> object:
    """Load a trained model from a pickle file.

    Args:
        path: Path to the model pickle file.

    Returns:
        Loaded model object.

    Raises:
        FileNotFoundError: If the model file does not exist.
    """
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    return model


def evaluate(
    model: object,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    output_dir: str = "backend/ml/artifacts",
) -> dict:
    """Evaluate model on test data and save results.

    Computes PR-AUC, confusion matrix, classification report, generates
    and saves a precision-recall curve plot, and writes evaluation_results.json.

    Args:
        model: Trained model with predict_proba method.
        X_test: Test features.
        y_test: Test labels.
        output_dir: Directory to save evaluation artifacts.

    Returns:
        Dictionary containing evaluation metrics and reports.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    # Metrics
    pr_auc = average_precision_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    report_text = classification_report(y_test, y_pred)

    # Precision-Recall curve
    precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(recall, precision, color="blue", lw=2, label=f"PR-AUC = {pr_auc:.4f}")
    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_title("Precision-Recall Curve", fontsize=14)
    ax.legend(loc="best", fontsize=11)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.grid(True, alpha=0.3)

    pr_curve_path = output_path / "pr_curve.png"
    fig.savefig(pr_curve_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Compile results
    results = {
        "pr_auc": float(pr_auc),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "classification_report_text": report_text,
        "test_samples": int(len(y_test)),
        "positive_samples": int(y_test.sum()),
        "negative_samples": int(len(y_test) - y_test.sum()),
        "pr_curve_path": str(pr_curve_path),
    }

    # Save results
    results_path = output_path / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Evaluation results saved to {results_path}")
    print(f"PR curve saved to {pr_curve_path}")

    return results


def main() -> None:
    """Run model evaluation on test data."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard ML Model Evaluation"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="backend/ml/artifacts/model.pkl",
        help="Path to trained model pickle file (default: backend/ml/artifacts/model.pkl)",
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
        default="backend/ml/artifacts",
        help="Directory to save evaluation artifacts (default: backend/ml/artifacts)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("EncryptionGuard ML Model Evaluation")
    print("=" * 60)

    # Load model
    print("\n[1/3] Loading model...")
    model = load_model(args.model_path)
    print(f"  Model type: {type(model).__name__}")

    # Load and split data
    print("\n[2/3] Loading test data...")
    df = load_data(args.data_dir)
    _, _, test_df = create_splits(df)

    feature_names = [
        "total_orders",
        "total_refunds",
        "total_amount",
        "avg_amount",
        "max_amount",
        "refund_rate",
        "refund_ratio",
        "high_amount",
    ]

    X_test = test_df[feature_names]
    y_test = test_df["label"]
    print(f"  Test samples: {len(X_test)}")
    print(f"  Abuse rate: {y_test.mean():.2%}")

    # Evaluate
    print("\n[3/3] Evaluating model...")
    results = evaluate(model, X_test, y_test, args.output_dir)

    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"  PR-AUC: {results['pr_auc']:.4f}")
    print(f"\nConfusion Matrix:")
    cm = np.array(results["confusion_matrix"])
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TP={cm[1,1]}")
    print(f"\nClassification Report:")
    print(results["classification_report_text"])
    print("=" * 60)


if __name__ == "__main__":
    main()
