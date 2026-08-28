"""
Tests for the data split / scenario generator.

Covers:
- No ring leakage (ring_id stays within its scenario)
- No scenario leakage (scenario_id is unique per scenario)
- Temporal ordering (events within a scenario are chronologically sorted)
"""

import pytest
from datetime import datetime

from backend.data.generator import ScenarioGenerator
from backend.data.scenarios import ScenarioType, SCENARIOS


class TestNoRingLeakage:
    """Ring IDs must not leak across scenarios."""

    def test_ring_ids_unique_per_scenario(self):
        """Each scenario should have a distinct ring_id (or None for normal)."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=1)

        ring_ids_by_scenario = {}
        for scenario in data:
            sid = scenario["scenario_id"]
            rings = {e.get("ring_id") for e in scenario["events"]}
            ring_ids_by_scenario[sid] = rings

        # Collect all non-None ring_ids
        all_rings = set()
        for rings in ring_ids_by_scenario.values():
            non_none = {r for r in rings if r is not None}
            all_rings.update(non_none)

        # Each non-None ring_id should appear in exactly one scenario
        for ring_id in all_rings:
            scenarios_with_ring = [
                sid
                for sid, rings in ring_ids_by_scenario.items()
                if ring_id in rings
            ]
            assert len(scenarios_with_ring) == 1, (
                f"Ring {ring_id} leaked into scenarios: {scenarios_with_ring}"
            )

    def test_normal_scenarios_have_no_ring(self):
        """NORMAL scenarios should not have any ring_id assigned."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=1)

        for scenario in data:
            if scenario["scenario_type"] == ScenarioType.NORMAL.value:
                for event in scenario["events"]:
                    assert event.get("ring_id") is None, (
                        f"NORMAL scenario has ring_id: {event['ring_id']}"
                    )


class TestNoScenarioLeakage:
    """Scenario IDs must be unique — no event should carry a foreign scenario_id."""

    def test_scenario_ids_are_globally_unique(self):
        """Every scenario_id in the generated data should be unique."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=2)

        ids = [s["scenario_id"] for s in data]
        assert len(ids) == len(set(ids)), "Duplicate scenario_ids found"

    def test_events_belong_to_own_scenario(self):
        """Each event's scenario_id should match its parent scenario."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=1)

        for scenario in data:
            sid = scenario["scenario_id"]
            for event in scenario["events"]:
                assert event.get("scenario_id") == sid, (
                    f"Event has scenario_id={event.get('scenario_id')}, "
                    f"expected {sid}"
                )


class TestTemporalOrdering:
    """Events within a scenario must be chronologically ordered."""

    def test_events_are_sorted_by_time(self):
        """Events should be in non-decreasing timestamp order."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=1)

        for scenario in data:
            timestamps = []
            for event in scenario["events"]:
                ts = event.get("generated_at")
                if ts is not None:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)
                    timestamps.append(ts)

            assert timestamps == sorted(timestamps), (
                f"Events in scenario {scenario['scenario_id']} are not "
                f"temporally ordered"
            )

    def test_refunds_after_payments(self):
        """Refund events should occur after their corresponding payment events."""
        gen = ScenarioGenerator(seed=42)
        data = gen.generate(num_merchants=1)

        for scenario in data:
            payment_times = {}
            refund_times = {}

            for event in scenario["events"]:
                ts = event.get("generated_at")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)

                entity_id = event.get("entity_id", "")
                event_type = event.get("event_type", "")

                if "payment" in event_type.lower() or event.get("entity_type") == "payment":
                    payment_times[entity_id] = ts
                elif "refund" in event_type.lower() or event.get("entity_type") == "refund":
                    refund_times[entity_id] = ts

            # For any refund that references a payment, the refund must come after
            for event in scenario["events"]:
                if event.get("entity_type") == "refund":
                    payload = event.get("payload", {})
                    if isinstance(payload, str):
                        import json
                        payload = json.loads(payload)
                    payment_id = (
                        payload.get("refund", {}).get("entity", {}).get("payment_id")
                        or payload.get("payment_id")
                    )
                    if payment_id and payment_id in payment_times:
                        refund_ts = event.get("generated_at")
                        if isinstance(refund_ts, str):
                            refund_ts = datetime.fromisoformat(refund_ts)
                        assert refund_ts >= payment_times[payment_id], (
                            f"Refund {event.get('entity_id')} occurred before "
                            f"payment {payment_id}"
                        )
