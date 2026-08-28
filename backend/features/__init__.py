"""
Shared feature library — used by both online scoring (app/) and offline training (ml/).
"""

from backend.features.schema import FeatureVector
from backend.features.velocity import compute_velocity_features, update_velocity_counters
from backend.features.graph import compute_graph_features, upsert_graph_entities

__all__ = [
    "FeatureVector",
    "compute_velocity_features",
    "update_velocity_counters",
    "compute_graph_features",
    "upsert_graph_entities",
]
