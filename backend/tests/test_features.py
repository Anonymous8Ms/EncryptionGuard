"""
Tests for FeatureVector schema validation.

Covers:
  1. Construction with all defaults
  2. Partial construction (only required fields)
  3. Serialisation round-trip (dict → model → dict)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.features.schema import FeatureVector


class TestFeatureVector:
    """Pydantic FeatureVector model tests."""

    def test_defaults(self):
        """All optional fields should default to zero / None."""
        fv = FeatureVector(
            account_id="acct_001",
            merchant_id="mch_001",
            reference_timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )
        assert fv.refund_count_24h == 0
        assert fv.refund_amount_7d == 0.0
        assert fv.connected_component_size == 0
        assert fv.pagerank_score == 0.0
        assert fv.community_id is None
        assert fv.event_label is None

    def test_partial_construction(self):
        """Only required fields + a subset of optional fields."""
        fv = FeatureVector(
            account_id="acct_002",
            merchant_id="mch_002",
            reference_timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            refund_count_24h=3,
            refund_amount_24h=150.50,
            connected_component_size=7,
        )
        assert fv.refund_count_24h == 3
        assert fv.refund_amount_24h == 150.50
        assert fv.connected_component_size == 7
        # Fields not supplied should still be defaults
        assert fv.order_count_24h == 0
        assert fv.shared_ip_count == 0

    def test_serialisation_round_trip(self):
        """model_dump → FeatureVector reconstruction should be lossless."""
        original = FeatureVector(
            account_id="acct_003",
            merchant_id="mch_003",
            reference_timestamp=datetime(2025, 3, 20, tzinfo=timezone.utc),
            refund_count_24h=5,
            refund_amount_24h=250.0,
            order_count_7d=12,
            unique_devices_24h=3,
            connected_component_size=10,
            weighted_degree=4.5,
            pagerank_score=0.042,
            community_id=42,
            event_label=1,
            ring_id="RING_001",
            scenario_id="scn_abc",
        )
        data = original.model_dump()
        restored = FeatureVector(**data)
        assert restored.account_id == original.account_id
        assert restored.refund_count_24h == original.refund_count_24h
        assert restored.pagerank_score == original.pagerank_score
        assert restored.community_id == original.community_id
        assert restored.event_label == original.event_label
        assert restored.ring_id == original.ring_id
