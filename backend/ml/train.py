"""
EncryptionGuard ML Training Pipeline
=====================================

XGBoost-based classification pipeline with Optuna hyperparameter tuning
for detecting encryption abuse patterns in e-commerce order data.

Usage:
    python -m backend.ml.train --data-dir data/ --output-dir backend/ml/artifacts/
"""

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from xgboost import XGBClassifier

# Suppress Optuna logging for cleaner output
optuna.logging.set_verbosity(optuna.logging.WARNING)


def load_data(data_dir: str) -> pd.DataFrame:
    """Load generated scenario data and aggregate features per account."""
    data_path = Path(data_dir) / "output" / "all_scenarios.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Generated data not found: {data_path}\nRun: python -m data.generator")

    with open(data_path, "r") as f:
        scenarios = json.load(f)

    rows = []
    for scenario in scenarios:
        label = scenario["events"][0]["event_label"] if scenario["events"] else 0
        ring_id = scenario["events"][0].get("ring_id") if scenario["events"] else None
        scenario_id = scenario.get("scenario_id", "unknown")

        # Build order_id -> account_id mapping
        order_to_acct = {}
        for o in scenario.get("orders", []):
            order_to_acct[o["order_id"]] = o["account_id"]

        for acct in scenario["accounts"]:
            acct_id = acct["account_id"]
            acct_orders = [o for o in scenario.get("orders", []) if o["account_id"] == acct_id]
            acct_order_ids = {o["order_id"] for o in acct_orders}
            acct_payments = [p for p in scenario.get("payments", []) if p["order_id"] in acct_order_ids]
            acct_payment_ids = {p["payment_id"] for p in acct_payments}
            acct_refunds = [r for r in scenario.get("refunds", []) if r["payment_id"] in acct_payment_ids]
            total_amount = sum(o.get("amount_cents", 0) for o in acct_orders)

            rows.append({
                "account_id": acct_id,
                "scenario_id": scenario_id,
                "ring_id": ring_id,
                "total_orders": len(acct_orders),
                "total_refunds": len(acct_refunds),
                "total_amount": total_amount,
                "avg_amount": total_amount / len(acct_orders) if acct_orders else 0,
                "max_amount": max((o.get("amount_cents", 0) for o in acct_orders), default=0),
                "refund_rate": len(acct_refunds) / len(acct_orders) if acct_orders else 0,
                "refund_ratio": len(acct_refunds) / total_amount if total_amount > 0 else 0,
                "high_amount": int(max((o.get("amount_cents", 0) for o in acct_orders), default=0) > 100000),
                "label": label,
            })

    return pd.DataFrame(rows)


def create_splits(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data into train, validation, and test sets.

    Sorts by scenario_id as a time proxy and performs a 60/20/20 sequential
    split (no shuffle) to respect temporal ordering.

    Args:
        df: DataFrame with features and label column.

    Returns:
        Tuple of (train, val, test) DataFrames.
    """
    df_sorted = df.sort_values("scenario_id").reset_index(drop=True)

    n = len(df_sorted)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)

    train = df_sorted.iloc[:train_end]
    val = df_sorted.iloc[train_end:val_end]
    test = df_sorted.iloc[val_end:]

    return train, val, test


def train_baseline(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> tuple[LogisticRegression, float]:
    """Train a logistic regression baseline model.

    Args:
        X_train: Training features.
        y_train: Training labels.
        X_val: Validation features.
        y_val: Validation labels.

    Returns:
        Tuple of (trained model, PR-AUC score on validation set).
    """
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred_proba = model.predict_proba(X_val)[:, 1]
    score = average_precision_score(y_val, y_pred_proba)

    return model, score


def objective(
    trial: optuna.Trial,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> float:
    """Optuna objective function for XGBoost hyperparameter tuning.

    Searches over learning_rate, max_depth, subsample, colsample_bytree,
    min_child_weight, gamma, and scale_pos_weight.

    Args:
        trial: Optuna trial object.
        X_train: Training features.
        y_train: Training labels.
        X_val: Validation features.
        y_val: Validation labels.

    Returns:
        PR-AUC score on validation set.
    """
    params = {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, 10.0),
    }

    model = XGBClassifier(
        **params,
        n_estimators=200,
        use_label_encoder=False,
        eval_metric="aucpr",
        random_state=42,
        verbosity=0,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    y_pred_proba = model.predict_proba(X_val)[:, 1]
    score = average_precision_score(y_val, y_pred_proba)

    return score


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    n_trials: int = 100,
) -> tuple[XGBClassifier, float, dict]:
    """Train XGBoost model with Optuna hyperparameter optimization.

    Runs an Optuna study to maximize PR-AUC, then trains a final model
    using the best hyperparameters found.

    Args:
        X_train: Training features.
        y_train: Training labels.
        X_val: Validation features.
        y_val: Validation labels.
        n_trials: Number of Optuna trials to run.

    Returns:
        Tuple of (trained model, best PR-AUC score, best hyperparameters dict).
    """
    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    best_params = study.best_params
    best_score = study.best_value

    # Train final model with best params
    final_model = XGBClassifier(
        **best_params,
        n_estimators=300,
        use_label_encoder=False,
        eval_metric="aucpr",
        random_state=42,
        verbosity=0,
    )
    final_model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    return final_model, best_score, best_params


def save_artifacts(
    model: XGBClassifier,
    baseline: LogisticRegression,
    feature_names: list[str],
    best_params: dict,
    val_score: float,
    output_dir: str = "backend/ml/artifacts",
) -> None:
    """Save trained model artifacts to disk.

    Saves the XGBoost model, baseline model, and metadata JSON.

    Args:
        model: Trained XGBoost model.
        baseline: Trained baseline logistic regression model.
        feature_names: List of feature names used in training.
        best_params: Best hyperparameters from Optuna study.
        val_score: Validation PR-AUC score.
        output_dir: Directory to save artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save XGBoost model
    with open(output_path / "model.pkl", "wb") as f:
        pickle.dump(model, f)

    # Save baseline model
    with open(output_path / "baseline_model.pkl", "wb") as f:
        pickle.dump(baseline, f)

    # Save metadata
    metadata = {
        "model_type": "XGBClassifier",
        "baseline_type": "LogisticRegression",
        "feature_names": feature_names,
        "hyperparameters": best_params,
        "validation_prauc": val_score,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "n_features": len(feature_names),
    }

    with open(output_path / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Artifacts saved to {output_path}/")


def main() -> None:
    """Run the full training pipeline."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard ML Training Pipeline"
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
        help="Directory to save model artifacts (default: backend/ml/artifacts)",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=100,
        help="Number of Optuna trials (default: 100)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("EncryptionGuard ML Training Pipeline")
    print("=" * 60)

    # Load data
    print("\n[1/5] Loading data...")
    df = load_data(args.data_dir)
    print(f"  Loaded {len(df)} accounts")
    print(f"  Abuse rate: {df['label'].mean():.2%}")

    # Create splits
    print("\n[2/5] Creating train/val/test splits...")
    train_df, val_df, test_df = create_splits(df)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    # Define features
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

    X_train = train_df[feature_names]
    y_train = train_df["label"]
    X_val = val_df[feature_names]
    y_val = val_df["label"]
    X_test = test_df[feature_names]
    y_test = test_df["label"]

    # Train baseline
    print("\n[3/5] Training baseline (LogisticRegression)...")
    baseline, baseline_score = train_baseline(X_train, y_train, X_val, y_val)
    print(f"  Baseline PR-AUC: {baseline_score:.4f}")

    # Train XGBoost with Optuna
    print(f"\n[4/5] Training XGBoost with Optuna ({args.n_trials} trials)...")
    model, best_score, best_params = train_xgboost(
        X_train, y_train, X_val, y_val, n_trials=args.n_trials
    )
    print(f"  Best PR-AUC: {best_score:.4f}")
    print(f"  Best params: {best_params}")

    # Save artifacts
    print("\n[5/5] Saving artifacts...")
    save_artifacts(
        model, baseline, feature_names, best_params, best_score, args.output_dir
    )

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"  Baseline PR-AUC: {baseline_score:.4f}")
    print(f"  XGBoost PR-AUC:  {best_score:.4f}")
    print(f"  Improvement:     {best_score - baseline_score:+.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
