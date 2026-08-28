"""
Model Card Generator
====================

Reads ``metadata.json`` (produced by ``train.py``) and
``evaluation_results.json`` (produced by ``evaluate.py``) and generates a
comprehensive ``MODEL_CARD.md`` following the Model Cards for Model
Reporting framework (Mitchell et al., 2019).

Usage::

    python -m backend.ml.model_card \\
        --metadata ./artifacts/metadata.json \\
        --evaluation ./artifacts/evaluation_results.json \\
        --output ./MODEL_CARD.md
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def generate_model_card(
    metadata_path: str | Path,
    eval_path: str | Path,
    output_path: str | Path = "MODEL_CARD.md",
) -> str:
    """Generate a MODEL_CARD.md from training metadata and evaluation results.

    Parameters
    ----------
    metadata_path : str or Path
        Path to ``metadata.json`` produced by the training pipeline.
    eval_path : str or Path
        Path to ``evaluation_results.json`` produced by the evaluation script.
    output_path : str or Path
        Destination for the generated Markdown file.

    Returns
    -------
    str
        The full Markdown content of the model card.
    """
    with open(metadata_path, "r", encoding="utf-8") as fh:
        metadata: Dict[str, Any] = json.load(fh)

    with open(eval_path, "r", encoding="utf-8") as fh:
        evaluation: Dict[str, Any] = json.load(fh)

    # Unpack commonly used fields
    model_type = metadata.get("model_type", "Unknown")
    baseline_type = metadata.get("baseline_type", "Unknown")
    features = metadata.get("feature_names", [])
    hyperparams = metadata.get("hyperparameters", {})
    val_pr_auc = metadata.get("validation_pr_auc", "N/A")
    created_at = metadata.get("created_at", datetime.now(timezone.utc).isoformat())
    xgb_ver = metadata.get("xgboost_version", "N/A")
    optuna_ver = metadata.get("optuna_version", "N/A")

    test_pr_auc = evaluation.get("pr_auc", "N/A")
    cm = evaluation.get("confusion_matrix", [[0, 0], [0, 0]])
    report = evaluation.get("classification_report", {})

    # Format confusion matrix
    if len(cm) == 2 and len(cm[0]) == 2:
        cm_text = (
            f"| | Predicted Legit | Predicted Abuse |\n"
            f"|---|---|---|\n"
            f"| **Actual Legit** | {cm[0][0]} (TN) | {cm[0][1]} (FP) |\n"
            f"| **Actual Abuse** | {cm[1][0]} (FN) | {cm[1][1]} (TP) |"
        )
    else:
        cm_text = f"```\n{cm}\n```"

    # Format classification report rows for class 0 and 1
    def _fmt_class(cls_key: str, label: str) -> str:
        cls = report.get(cls_key, {})
        if not cls:
            return ""
        return (
            f"| {label} | {cls.get('precision', 'N/A'):.4f} | "
            f"{cls.get('recall', 'N/A'):.4f} | {cls.get('f1-score', 'N/A'):.4f} | "
            f"{cls.get('support', 'N/A')} |\n"
        )

    report_table = (
        "| Class | Precision | Recall | F1-Score | Support |\n"
        "|---|---|---|---|---|\n"
        + _fmt_class("0", "Legitimate")
        + _fmt_class("1", "Abuse")
    )

    # Format hyperparameters
    hp_lines = "\n".join(
        f"| `{k}` | `{v}` |" for k, v in hyperparams.items()
    )
    hp_table = (
        "| Hyperparameter | Value |\n|---|---|\n" + hp_lines
        if hp_lines
        else "_No hyperparameters recorded._"
    )

    # Format feature list
    feature_list = "\n".join(f"- `{f}`" for f in features) if features else "- _None recorded_"

    # --- Assemble the model card -------------------------------------------
    card = f"""\
# EncryptionGuard -- Model Card

> Auto-generated on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

---

## 1. Model Details

| Field | Value |
|---|---|
| **Model type** | {model_type} |
| **Baseline** | {baseline_type} |
| **XGBoost version** | {xgb_ver} |
| **Optuna version** | {optuna_ver} |
| **Created at** | {created_at} |

## 2. Intended Use

- **Primary use case**: Detect accounts exhibiting encryption-abuse
  patterns based on ordering and refund behaviour.
- **Intended users**: Fraud-operations team; automated scoring service.
- **Out-of-scope uses**: Not suitable for detecting non-ordering abuse
  vectors (e.g., credential stuffing, phishing). Should not be used as
  the sole decision-maker without human review.

## 3. Training Data

- **Source**: ``events.json`` -- synthetic / labelled event logs
  containing per-order records with ``account_id``, ``order_amount``,
  ``is_refund``, ``event_label``, and ``scenario_id``.
- **Split strategy**: Chronological (sorted by ``scenario_id``) with a
  60 / 20 / 20 train / validation / test ratio. No shuffling to
  preserve temporal ordering.
- **Class imbalance**: Handled via ``class_weight="balanced"`` (baseline)
  and ``scale_pos_weight`` (XGBoost).

## 4. Features

{feature_list}

### Feature Engineering Notes

- ``refund_rate`` and ``refund_ratio`` guard against division by zero
  (NaN filled to 0.0).
- ``high_amount`` counts orders above the 90th-percentile amount
  threshold.

## 5. Hyperparameters (XGBoost)

{hp_table}

## 6. Performance

### Validation

| Metric | Value |
|---|---|
| **PR-AUC** | {val_pr_auc} |

### Test

| Metric | Value |
|---|---|
| **PR-AUC** | {test_pr_auc} |

#### Confusion Matrix (Test)

{cm_text}

#### Classification Report (Test)

{report_table}

## 7. Limitations

1. **Temporal drift**: Model trained on historical scenario ordering;
   performance may degrade as abuse tactics evolve. Retrain regularly.
2. **Feature scope**: Only order/refund aggregates are used; behavioural
   signals (session duration, device fingerprint) are not captured.
3. **Threshold sensitivity**: Default decision threshold is 0.5; tuning
   for precision vs. recall trade-off is application-dependent.
4. **Data quality**: Model assumes ``events.json`` is complete and
   correctly labelled. Missing or mislabelled events will degrade
   performance.

## 8. Ethical Considerations

- **False positives**: Legitimate accounts flagged as abusive may
  experience friction (manual review, temporary holds). Mitigation:
  human-in-the-loop review for high-confidence false-positive appeals.
- **Fairness**: The model does not use demographic features, but proxy
  correlations in ordering patterns could introduce bias. Periodic
  fairness audits are recommended.
- **Transparency**: This model card and the evaluation results are
  versioned alongside the model artefacts for auditability.

## 9. Monitoring & Maintenance

- **Retraining cadence**: Monthly, or sooner if PR-AUC on live data
  drops below 0.80 of the validation score.
- **Data drift**: Monitor feature distributions (KS-test) between
  training data and incoming production data.
- **Alerting**: Trigger alerts when live PR-AUC falls below the
  validation baseline or when class-ratio shifts by >20%.
- **Versioning**: Every model artefact is stored with ``metadata.json``
  containing training timestamp, hyperparameters, and library versions.

---

*Generated by EncryptionGuard ML Pipeline v5.0.0*
"""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(card)

    logger.info("Model card written to %s", output)
    return card


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def main() -> None:
    """Generate a model card from metadata and evaluation results."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard model card generator"
    )
    parser.add_argument(
        "--metadata",
        type=str,
        default="artifacts/metadata.json",
        help="Path to metadata.json (default: artifacts/metadata.json)",
    )
    parser.add_argument(
        "--evaluation",
        type=str,
        default="artifacts/evaluation_results.json",
        help="Path to evaluation_results.json (default: artifacts/evaluation_results.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="MODEL_CARD.md",
        help="Output path for MODEL_CARD.md (default: MODEL_CARD.md)",
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

    generate_model_card(
        metadata_path=args.metadata,
        eval_path=args.evaluation,
        output_path=args.output,
    )
    logger.info("Done.")


if __name__ == "__main__":
    main()
