# EncryptionGuard Model Card

**Generated**: 2026-09-03 13:03:27 UTC
**Training Date**: 2026-09-03T13:00:33.296668+00:00

---

## Model Details

| Property | Value |
|----------|-------|
| Model Type | XGBClassifier |
| Baseline Model | LogisticRegression |
| Number of Features | 8 |
| Validation PR-AUC | 0.8750 |
| Test PR-AUC | 0.7222 |

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
| Test Samples | 72 |
| Positive (Abuse) Samples | 52 |
| Negative (Legitimate) Samples | 20 |
| Abuse Rate | 72.22% |

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
| total_orders | Total number of orders placed by the account |
| total_refunds | Total number of refund events |
| total_amount | Sum of all order amounts |
| avg_amount | Average order amount |
| max_amount | Maximum single order amount |
| refund_rate | Ratio of refunds to total orders |
| refund_ratio | Ratio of refunds to total amount |
| high_amount | Binary flag: 1 if max order > $1000 |

---

## Hyperparameters

The following hyperparameters were selected via Optuna optimization
(maximizing validation PR-AUC):

| Parameter | Value |
|-----------|-------|
| learning_rate | 0.01144654350951607 |
| max_depth | 3 |
| subsample | 0.9004080615772506 |
| colsample_bytree | 0.717395059673428 |
| min_child_weight | 5 |
| gamma | 4.878603158874204 |
| scale_pos_weight | 9.766326253704815 |

---

## Performance

### Test Set Results

| Metric | Value |
|--------|-------|
| PR-AUC | 0.7222 |
| Accuracy | 0.7222 |

### Confusion Matrix

|  | Predicted Legitimate | Predicted Abuse |
|--|---------------------|-----------------|
| **Actual Legitimate** | 0 (TN) | 20 (FP) |
| **Actual Abuse** | 0 (FN) | 52 (TP) |

### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Legitimate (0) | 0.0000 | 0.0000 | 0.0000 | 20.0 |
| Abuse (1) | 0.7222 | 1.0000 | 0.8387 | 52.0 |

### Aggregate Metrics

| Metric | Precision | Recall | F1-Score |
|--------|-----------|--------|----------|
| Macro Avg | 0.3611 | 0.5000 | 0.4194 |
| Weighted Avg | 0.5216 | 0.7222 | 0.6057 |

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

- **Recommended**: Retrain monthly or when PR-AUC drops below 0.6500
  (90% of test performance).
- **Trigger-based**: Retrain immediately if a new abuse pattern is identified
  that the model fails to detect.

### Version History

| Version | Date | PR-AUC | Notes |
|---------|------|--------|-------|
| 1.0 | 2026-09-03 | 0.7222 | Initial model with XGBoost + Optuna |

---

## Contact

For questions about this model, please contact the EncryptionGuard ML team.
