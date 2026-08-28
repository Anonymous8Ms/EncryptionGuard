"""
EncryptionGuard ML Pipeline
============================

Machine learning module for detecting encryption abuse patterns in
account ordering behaviour. Provides:

- **train.py** -- XGBoost training pipeline with Optuna hyperparameter tuning
- **evaluate.py** -- Model evaluation with PR-AUC, confusion matrix, and
  classification report
- **model_card.py** -- Automated model card generation (MODEL_CARD.md)

Usage::

    python -m backend.ml.train --data-dir ./data --output-dir ./artifacts
    python -m backend.ml.evaluate --model-path ./artifacts/model.pkl --data-dir ./data
    python -m backend.ml.model_card --metadata ./artifacts/metadata.json \\
        --evaluation ./artifacts/evaluation_results.json --output ./MODEL_CARD.md
"""

__version__ = "5.0.0"
