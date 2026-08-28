"""
Tests for data split utilities.

Covers:
  1. Deterministic split with fixed seed
  2. Split ratios sum to 1.0 and produce correct proportions
  3. No data leakage — train/val/test sets are disjoint
"""

from __future__ import annotations

import random
from typing import Any


def split_data(
    data: list[Any],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, list[Any]]:
    """Split a list into train / val / test subsets.

    Args:
        data: List of items to split.
        train_ratio: Fraction for training set.
        val_ratio: Fraction for validation set.
        test_ratio: Fraction for test set.
        seed: Random seed for reproducibility.

    Returns:
        Dict with keys ``train``, ``val``, ``test``.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-9, (
        f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
    )

    rng = random.Random(seed)
    shuffled = list(data)
    rng.shuffle(shuffled)

    n = len(shuffled)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:val_end],
        "test": shuffled[val_end:],
    }


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSplitData:
    """Data splitting utility tests."""

    def test_deterministic_split(self):
        """Same seed → same split every time."""
        data = list(range(100))
        split1 = split_data(data, seed=42)
        split2 = split_data(data, seed=42)
        assert split1["train"] == split2["train"]
        assert split1["val"] == split2["val"]
        assert split1["test"] == split2["test"]

    def test_split_ratios(self):
        """Split proportions should approximate the requested ratios."""
        data = list(range(1000))
        split = split_data(data, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42)
        total = len(split["train"]) + len(split["val"]) + len(split["test"])
        assert total == 1000
        # Allow ±2% tolerance for rounding
        assert abs(len(split["train"]) / 1000 - 0.7) < 0.02
        assert abs(len(split["val"]) / 1000 - 0.15) < 0.02
        assert abs(len(split["test"]) / 1000 - 0.15) < 0.02

    def test_no_data_leakage(self):
        """Train, val, and test sets must be completely disjoint."""
        data = list(range(500))
        split = split_data(data, seed=99)
        train_set = set(split["train"])
        val_set = set(split["val"])
        test_set = set(split["test"])
        assert len(train_set & val_set) == 0, "Train/val overlap detected"
        assert len(train_set & test_set) == 0, "Train/test overlap detected"
        assert len(val_set & test_set) == 0, "Val/test overlap detected"
        # Union should equal original data
        assert train_set | val_set | test_set == set(data)
