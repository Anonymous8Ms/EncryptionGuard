"""
EncryptionGuard ML Pipeline
============================

Machine learning module for detecting encryption abuse patterns in
e-commerce order data. Provides XGBoost-based classification with
Optuna hyperparameter tuning, model evaluation, and model card generation.

Modules:
    train: XGBoost training pipeline with Optuna hyperparameter optimization.
    evaluate: Model evaluation with PR-AUC, confusion matrix, and PR curve.
    model_card: Automated model card generation from training metadata.
"""

__version__ = "5.0.0"
