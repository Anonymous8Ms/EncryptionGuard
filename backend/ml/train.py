"""
XGBoost Training Pipeline with Optuna Hyperparameter Tuning
============================================================

Loads event data from ``events.json``, aggregates per-account features,
splits chronologically, trains a Logistic Regression baseline and an
XGBoost model tuned via Optuna, then persists all artefacts.

Usage::

    python -m backend.ml.train --data-dir ./data --output-dir ./artifacts
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import optuna
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature columns produced by load_data
# ---------------------------------------------------------------------------
FEATURE_COLS: List[str] = [
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
# Data loading & feature engineering
# ---------------------------------------------------------------------------
def load_data(data_dir: str | Path) -> pd.DataFrame:
    """Load ``events.json`` and aggregate per-account features.

    Parameters
    ----------
    data_dir : str or Path
        Directory containing ``events.json``.

    Returns
    -------
    pd.DataFrame
        One row per account with engineered features and a binary ``label``
        column (1 = abuse, 0 = legitimate).
    """
    data_path = Path(data_dir) / "events.json"
    logger.info("Loading events from %s", data_path)

    with open(data_path, "r", encoding="utf-8") as fh:
        raw: List[Dict[str, Any]] = json.load(fh)

    df = pd.DataFrame(raw)

    # --- per-account aggregation -------------------------------------------
    agg = df.groupby("account_id").agg(
        total_orders=("order_amount", "count"),
        total_refunds=("is_refund", "sum"),
        total_amount=("order_amount", "sum"),
        avg_amount=("order_amount", "mean"),
        max_amount=("order_amount", "max"),
        scenario_id=("scenario_id", "first"),  # keep for time-based split
    )

    # Derived features (guard against division by zero)
    agg["refund_rate"] = agg["total_refunds"] / agg["total_orders"].replace(0, np.nan)
    agg["refund_rate"] = agg["refund_rate"].fillna(0.0)

    agg["refund_ratio"] = agg["total_refunds"] / agg["total_orders"].replace(0, np.nan)
    agg["refund_ratio"] = agg["refund_ratio"].fillna(0.0)

    # Binary flag: order amount exceeds a high-amount threshold (90th pctile)
    high_threshold = df["order_amount"].quantile(0.9)
    high_counts = (
        df[df["order_amount"] >= high_threshold]
        .groupby("account_id")["order_amount"]
        .count()
    )
    agg["high_amount"] = high_counts.reindex(agg.index, fill_value=0)

    # --- labels ------------------------------------------------------------
    # Label is 1 when any event for the account has event_label == "abuse"
    abuse_accounts = set(
        df[df["event_label"] == "abuse"]["account_id"].unique()
    )
    agg["label"] = agg.index.isin(abuse_accounts).astype(int)

    logger.info(
        "Loaded %d accounts (%d abuse, %d legit)",
        len(agg),
        agg["label"].sum(),
        len(agg) - agg["label"].sum(),
    )
    return agg.reset_index()


# ---------------------------------------------------------------------------
# Train / validation / test splits (chronological, no shuffle)
# ---------------------------------------------------------------------------
def create_splits(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data chronologically by ``scenario_id`` (60/20/20).

    Parameters
    ----------
    df : pd.DataFrame
        Full dataset including ``scenario_id`` column.

    Returns
    -------
    train, val, test : pd.DataFrame
    """
    df_sorted = df.sort_values("scenario_id").reset_index(drop=True)
    n = len(df_sorted)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)

    train = df_sorted.iloc[:train_end]
    val = df_sorted.iloc[train_end:val_end]
    test = df_sorted.iloc[val_end:]

    logger.info(
        "Split sizes -- train: %d, val: %d, test: %d",
        len(train),
        len(val),
        len(test),
    )
    return train, val, test


# ---------------------------------------------------------------------------
# Baseline model
# ---------------------------------------------------------------------------
def train_baseline(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Tuple[LogisticRegression, float]:
    """Train a Logistic Regression baseline and return PR-AUC on validation.

    Parameters
    ----------
    X_train, y_train : training features and labels.
    X_val, y_val : validation features and labels.

    Returns
    -------
    model : LogisticRegression
    score : float  (PR-AUC on validation set)
    """
    logger.info("Training Logistic Regression baseline ...")
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )
    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_val)[:, 1]
    score = average_precision_score(y_val, y_prob)
    logger.info("Baseline PR-AUC: %.4f", score)
    return model, score


# ---------------------------------------------------------------------------
# Optuna objective for XGBoost
# ---------------------------------------------------------------------------
def objective(
    trial: optuna.trial.Trial,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> float:
    """Optuna objective: train XGBoost with sampled hyperparameters.

    Returns PR-AUC on the validation set (to be maximised).
    """
    params: Dict[str, Any] = {
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
        n_estimators=300,
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
    y_prob = model.predict_proba(X_val)[:, 1]
    return float(average_precision_score(y_val, y_prob))


# ---------------------------------------------------------------------------
# Full XGBoost training with Optuna
# ---------------------------------------------------------------------------
def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    n_trials: int = 100,
) -> Tuple[XGBClassifier, float, Dict[str, Any]]:
    """Run Optuna study and train final XGBoost model with best params.

    Parameters
    ----------
    X_train, y_train : training features and labels.
    X_val, y_val : validation features and labels.
    n_trials : int
        Number of Optuna trials.

    Returns
    -------
    model : XGBClassifier
    score : float  (best PR-AUC on validation)
    best_params : dict
    """
    logger.info("Starting Optuna study (%d trials) ...", n_trials)
    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    best_params = study.best_params
    best_score = study.best_value
    logger.info("Best PR-AUC: %.4f  params: %s", best_score, best_params)

    # Train final model with best params on train+val combined
    X_trainval = pd.concat([X_train, X_val], axis=0)
    y_trainval = pd.concat([y_train, y_val], axis=0)

    model = XGBClassifier(
        **best_params,
        n_estimators=500,
        use_label_encoder=False,
        eval_metric="aucpr",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_trainval, y_trainval, verbose=False)

    return model, best_score, best_params


# ---------------------------------------------------------------------------
# Save artefacts
# ---------------------------------------------------------------------------
def save_artifacts(
    model: XGBClassifier,
    baseline: LogisticRegression,
    feature_names: List[str],
    best_params: Dict[str, Any],
    val_score: float,
    output_dir: str | Path = "artifacts",
) -> None:
    """Persist trained models and metadata to *output_dir*.

    Files written:
    - ``model.pkl``          -- tuned XGBoost model
    - ``baseline_model.pkl`` -- Logistic Regression baseline
    - ``metadata.json``      -- feature names, hyperparameters, score, timestamp
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "model.pkl", "wb") as fh:
        pickle.dump(model, fh)
    logger.info("Saved model.pkl")

    with open(out / "baseline_model.pkl", "wb") as fh:
        pickle.dump(baseline, fh)
    logger.info("Saved baseline_model.pkl")

    metadata = {
        "model_type": "XGBClassifier",
        "baseline_type": "LogisticRegression",
        "feature_names": feature_names,
        "hyperparameters": best_params,
        "validation_pr_auc": val_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "xgboost_version": __import__("xgboost").__version__,
        "optuna_version": __import__("optuna").__version__,
    }
    with open(out / "metadata.json", "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info("Saved metadata.json")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the full training pipeline."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard XGBoost training pipeline"
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
        help="Directory for model artefacts (default: artifacts)",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=100,
        help="Number of Optuna trials (default: 100)",
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

    # 1. Load & engineer features
    df = load_data(args.data_dir)

    # 2. Chronological split
    train_df, val_df, test_df = create_splits(df)

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["label"]
    X_val = val_df[FEATURE_COLS]
    y_val = val_df["label"]

    # 3. Baseline
    baseline, baseline_score = train_baseline(X_train, y_train, X_val, y_val)

    # 4. XGBoost + Optuna
    model, xgb_score, best_params = train_xgboost(
        X_train, y_train, X_val, y_val, n_trials=args.n_trials
    )

    # 5. Persist
    save_artifacts(
        model=model,
        baseline=baseline,
        feature_names=FEATURE_COLS,
        best_params=best_params,
        val_score=xgb_score,
        output_dir=args.output_dir,
    )

    # Also save test split for later evaluation
    out = Path(args.output_dir)
    test_df.to_csv(out / "test_split.csv", index=False)
    logger.info("Saved test_split.csv")

    logger.info(
        "Pipeline complete -- baseline PR-AUC: %.4f, XGBoost PR-AUC: %.4f",
        baseline_score,
        xgb_score,
    )


if __name__ == "__main__":
    main()
