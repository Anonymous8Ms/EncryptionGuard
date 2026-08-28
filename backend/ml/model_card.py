"""
EncryptionGuard Model Card Generator
=====================================

Generates a comprehensive MODEL_CARD.md from training metadata and
evaluation results, following model card best practices for transparency
and responsible AI documentation.

Usage:
    python -m backend.ml.model_card \
        --metadata-path backend/ml/artifacts/metadata.json \
        --eval-path backend/ml/artifacts/evaluation_results.json \
        --output-path backend/ml/artifacts/MODEL_CARD.md
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def generate_model_card(
    metadata_path: str,
    eval_path: str,
    output_path: str,
) -> None:
    """Generate a MODEL_CARD.md from training metadata and evaluation results.

    Reads metadata.json and evaluation_results.json, then produces a
    comprehensive model card document covering model details, intended use,
    training data, features, hyperparameters, performance metrics, limitations,
    ethical considerations, and monitoring recommendations.

    Args:
        metadata_path: Path to metadata.json from training.
        eval_path: Path to evaluation_results.json from evaluation.
        output_path: Path to write the MODEL_CARD.md file.

    Raises:
        FileNotFoundError: If metadata or evaluation files do not exist.
    """
    # Load metadata
    meta_file = Path(metadata_path)
    if not meta_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_file}")
    with open(meta_file, "r") as f:
        metadata = json.load(f)

    # Load evaluation results
    eval_file = Path(eval_path)
    if not eval_file.exists():
        raise FileNotFoundError(f"Evaluation file not found: {eval_file}")
    with open(eval_file, "r") as f:
        eval_results = json.load(f)

    # Extract values
    model_type = metadata.get("model_type", "Unknown")
    baseline_type = metadata.get("baseline_type", "Unknown")
    feature_names = metadata.get("feature_names", [])
    hyperparameters = metadata.get("hyperparameters", {})
    val_prauc = metadata.get("validation_prauc", 0.0)
    training_ts = metadata.get("training_timestamp", "Unknown")
    n_features = metadata.get("n_features", len(feature_names))

    test_prauc = eval_results.get("pr_auc", 0.0)
    cm = eval_results.get("confusion_matrix", [[0, 0], [0, 0]])
    report = eval_results.get("classification_report", {})
    test_samples = eval_results.get("test_samples", 0)
    positive_samples = eval_results.get("positive_samples", 0)
    negative_samples = eval_results.get("negative_samples", 0)

    # Extract per-class metrics
    class_0 = report.get("0", {})
    class_1 = report.get("1", {})
    accuracy = report.get("accuracy", 0.0)
    macro_avg = report.get("macro avg", {})
    weighted_avg = report.get("weighted avg", {})

    # Format hyperparameters table
    hp_rows = "\n".join(
        f"| {k} | {v} |" for k, v in hyperparameters.items()
    )

    # Format features table
    feature_descriptions = {
        "total_orders": "Total number of orders placed by the account",
        "total_refunds": "Total number of refund events",
        "total_amount": "Sum of all order amounts",
        "avg_amount": "Average order amount",
        "max_amount": "Maximum single order amount",
        "refund_rate": "Ratio of refunds to total orders",
        "refund_ratio": "Ratio of refunds to total amount",
        "high_amount": "Binary flag: 1 if max order > $1000",
    }
    feature_rows = "\n".join(
        f"| {fname} | {feature_descriptions.get(fname, 'N/A')} |"
        for fname in feature_names
    )

    # Build model card
    model_card = f"""# EncryptionGuard Model Card

**Generated**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Training Date**: {training_ts}

---

## Model Details

| Property | Value |
|----------|-------|
| Model Type | {model_type} |
| Baseline Model | {baseline_type} |
| Number of Features | {n_features} |
| Validation PR-AUC | {val_prauc:.4f} |
| Test PR-AUC | {test_prauc:.4f} |

### Description

EncryptionGuard uses an XGBoost classifier to detect encryption abuse patterns
in e-commerce order data. The model identifies accounts exhibiting suspicious
ordering and refund behaviors that may indicate fraudulent exploitation of
encryption-related policies.

The model is trained with Optuna hyperparameter optimization to maximize the
Precision-Recall AUC metric, which is appropriate for the imbalanced nature
of abuse detection (typically few abuse cases relative to legitimate activity).

---

## Intended Use

### Primary Use Case

- **Real-time abuse detection**: Score incoming order events to flag accounts
  with suspicious patterns for manual review.
- **Batch screening**: Periodically scan all accounts to identify potential
  abuse that may have evaded real-time detection.

### Out-of-Scope Uses

- Automated account termination without human review
- Credit scoring or financial lending decisions
- Profiling based on protected characteristics
- Use outside the e-commerce encryption policy domain

---

## Training Data

| Metric | Value |
|--------|-------|
| Test Samples | {test_samples} |
| Positive (Abuse) Samples | {positive_samples} |
| Negative (Legitimate) Samples | {negative_samples} |
| Abuse Rate | {positive_samples / max(test_samples, 1):.2%} |

### Data Source

Training data consists of aggregated order and refund events from the
EncryptionGuard platform. Events are grouped by account to create per-account
behavioral features.

### Data Split

Data is split chronologically (sorted by scenario_id as a time proxy):
- **Training**: 60% (earliest events)
- **Validation**: 20%
- **Test**: 20% (latest events)

No shuffling is applied to preserve temporal ordering and prevent data leakage.

---

## Features

| Feature | Description |
|---------|-------------|
{feature_rows}

---

## Hyperparameters

The following hyperparameters were selected via Optuna optimization
(maximizing validation PR-AUC):

| Parameter | Value |
|-----------|-------|
{hp_rows}

---

## Performance

### Test Set Results

| Metric | Value |
|--------|-------|
| PR-AUC | {test_prauc:.4f} |
| Accuracy | {accuracy:.4f} |

### Confusion Matrix

|  | Predicted Legitimate | Predicted Abuse |
|--|---------------------|-----------------|
| **Actual Legitimate** | {cm[0][0]} (TN) | {cm[0][1]} (FP) |
| **Actual Abuse** | {cm[1][0]} (FN) | {cm[1][1]} (TP) |

### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Legitimate (0) | {class_0.get("precision", 0):.4f} | {class_0.get("recall", 0):.4f} | {class_0.get("f1-score", 0):.4f} | {class_0.get("support", 0)} |
| Abuse (1) | {class_1.get("precision", 0):.4f} | {class_1.get("recall", 0):.4f} | {class_1.get("f1-score", 0):.4f} | {class_1.get("support", 0)} |

### Aggregate Metrics

| Metric | Precision | Recall | F1-Score |
|--------|-----------|--------|----------|
| Macro Avg | {macro_avg.get("precision", 0):.4f} | {macro_avg.get("recall", 0):.4f} | {macro_avg.get("f1-score", 0):.4f} |
| Weighted Avg | {weighted_avg.get("precision", 0):.4f} | {weighted_avg.get("recall", 0):.4f} | {weighted_avg.get("f1-score", 0):.4f} |

---

## Limitations

1. **Temporal drift**: Model performance may degrade as user behavior patterns
   evolve over time. Regular retraining is recommended.

2. **Feature limitations**: The model relies on aggregated order/refund features
   only. It does not account for:
   - User demographics or account age
   - Product category information
   - Geographic or IP-based signals
   - Device fingerprinting

3. **Threshold sensitivity**: The default classification threshold (0.5) may
   not be optimal for all deployment scenarios. Threshold should be tuned
   based on the cost of false positives vs. false negatives.

4. **Data quality**: Model predictions are only as good as the input data.
   Missing or corrupted event data will degrade performance.

5. **Small dataset risk**: If trained on a small dataset, the model may
   overfit to specific patterns that do not generalize.

---

## Ethical Considerations

### Fairness

- The model should be regularly audited for disparate impact across
  demographic groups.
- Feature selection avoids protected characteristics (race, gender, age,
  religion, etc.).
- False positive rates should be monitored across account segments to
  ensure equitable treatment.

### Transparency

- All flagged accounts should receive a human review before any punitive
  action is taken.
- Account holders should be informed of the general criteria used for
  abuse detection.
- This model card provides full transparency into model design and
  performance.

### Privacy

- Training data is aggregated at the account level; no individual event
  details are stored in model artifacts.
- Model artifacts (pickle files) should be stored securely with
  appropriate access controls.

### Accountability

- A clear escalation path should exist for disputed flags.
- Model decisions should be logged for audit purposes.
- Regular bias audits should be conducted and documented.

---

## Monitoring and Maintenance

### Recommended Monitoring

1. **Performance monitoring**: Track PR-AUC on a rolling basis using
   labeled data from manual reviews.
2. **Data drift detection**: Monitor feature distributions for significant
   shifts from training data.
3. **Prediction drift**: Track the distribution of predicted probabilities
   over time.
4. **Fairness metrics**: Regularly compute false positive rates across
   account segments.

### Retraining Schedule

- **Recommended**: Retrain monthly or when PR-AUC drops below {test_prauc * 0.9:.4f}
  (90% of test performance).
- **Trigger-based**: Retrain immediately if a new abuse pattern is identified
  that the model fails to detect.

### Version History

| Version | Date | PR-AUC | Notes |
|---------|------|--------|-------|
| 1.0 | {training_ts[:10] if training_ts != "Unknown" else "N/A"} | {test_prauc:.4f} | Initial model with XGBoost + Optuna |

---

## Contact

For questions about this model, please contact the EncryptionGuard ML team.
"""

    # Write model card
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        f.write(model_card)

    print(f"Model card generated: {output}")


def main() -> None:
    """Generate model card from training and evaluation artifacts."""
    parser = argparse.ArgumentParser(
        description="EncryptionGuard Model Card Generator"
    )
    parser.add_argument(
        "--metadata-path",
        type=str,
        default="backend/ml/artifacts/metadata.json",
        help="Path to metadata.json (default: backend/ml/artifacts/metadata.json)",
    )
    parser.add_argument(
        "--eval-path",
        type=str,
        default="backend/ml/artifacts/evaluation_results.json",
        help="Path to evaluation_results.json (default: backend/ml/artifacts/evaluation_results.json)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="backend/ml/artifacts/MODEL_CARD.md",
        help="Output path for MODEL_CARD.md (default: backend/ml/artifacts/MODEL_CARD.md)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("EncryptionGuard Model Card Generator")
    print("=" * 60)

    generate_model_card(
        metadata_path=args.metadata_path,
        eval_path=args.eval_path,
        output_path=args.output_path,
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
