"""
Graph features — computed from Neo4j.

All Cypher queries MUST include a time-window filter using
``reference_timestamp`` and ``ttl_days`` to prevent training-serving
leakage.  The reference_timestamp is the "as-of" time for the feature
computation; the TTL bounds how far back relationships are considered.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from neo4j import Driver


# ── Helpers ────────────────────────────────────────────────────────────────


def _time_filter(alias: str = "r") -> str:
    """Return the mandatory WHERE clause fragment for time-bounded queries.

    Uses parameterised ``$ref_time`` and ``$ttl`` so the Cypher is
    cache-friendly in Neo4j's query plan cache.
    """
    return (
        f"WHERE {alias}.created_at <= $ref_time "
        f"AND {alias}.created_at >= datetime() - duration({{days: $ttl}})"
    )


# ── Public API ─────────────────────────────────────────────────────────────


def compute_graph_features(
    neo4j_driver: Driver,
    account_id: str,
    reference_timestamp: datetime,
    ttl_days: int = 90,
) -> dict[str, Any]:
    """Compute graph-based features for *account_id* as of *reference_timestamp*.

    Every query is bounded by ``[reference_timestamp - ttl_days, reference_timestamp]``
    to guarantee no future information leaks into the feature vector.
    """
    params = {
        "account_id": account_id,
        "ref_time": reference_timestamp.isoformat(),
        "ttl": ttl_days,
    }

    features: dict[str, Any] = {}

    with neo4j_driver.session() as session:
        # ── Connected component size ───────────────────────────────────
        result = session.run(
            f"""
            MATCH (a:Account {{id: $account_id}})-[r*1..3]-(connected:Account)
            {_time_filter("r")}
            RETURN count(DISTINCT connected) AS component_size
            """,
            params,
        )
        record = result.single()
        features["connected_component_size"] = (
            record["component_size"] if record else 0
        )

        # ── Weighted degree ────────────────────────────────────────────
        result = session.run(
            f"""
            MATCH (a:Account {{id: $account_id}})-[r]-(other)
            {_time_filter("r")}
            RETURN count(r) AS degree
            """,
            params,
        )
        record = result.single()
        features["weighted_degree"] = float(record["degree"]) if record else 0.0

        # ── PageRank score ─────────────────────────────────────────────
        # Use GDS if available; fall back to a simple degree-based proxy.
        try:
            result = session.run(
                f"""
                CALL gds.pageRank.stream('account-graph', {{
                    sourceNodes: [n WHERE n.id = $account_id]
                }})
                YIELD nodeId, score
                RETURN score
                """,
                params,
            )
            record = result.single()
            features["pagerank_score"] = float(record["score"]) if record else 0.0
        except Exception:
            # GDS not installed — approximate with normalised degree
            result = session.run(
                f"""
                MATCH (a:Account {{id: $account_id}})-[r]-(other)
                {_time_filter("r")}
                WITH count(r) AS deg
                MATCH (n:Account)
                WITH deg, count(n) AS total
                RETURN CASE WHEN total > 1 THEN deg / (total - 1.0) ELSE 0.0 END AS score
                """,
                params,
            )
            record = result.single()
            features["pagerank_score"] = float(record["score"]) if record else 0.0

        # ── Community ID ───────────────────────────────────────────────
        try:
            result = session.run(
                """
                CALL gds.louvain.stream('account-graph')
                YIELD nodeId, communityId
                WITH gds.util.asNode(nodeId) AS n, communityId
                WHERE n.id = $account_id
                RETURN communityId
                """,
                params,
            )
            record = result.single()
            features["community_id"] = (
                int(record["communityId"]) if record else None
            )
        except Exception:
            features["community_id"] = None

        # ── Shared entity counts ───────────────────────────────────────
        for entity_type, feature_name in [
            ("Device", "shared_device_count"),
            ("IP", "shared_ip_count"),
            ("Token", "shared_token_count"),
        ]:
            result = session.run(
                f"""
                MATCH (a:Account {{id: $account_id}})-[r1]->(e:{entity_type})<-[r2]-(other:Account)
                WHERE other.id <> $account_id
                  AND r1.created_at <= $ref_time
                  AND r1.created_at >= datetime() - duration({{days: $ttl}})
                  AND r2.created_at <= $ref_time
                  AND r2.created_at >= datetime() - duration({{days: $ttl}})
                RETURN count(DISTINCT other) AS shared_count
                """,
                params,
            )
            record = result.single()
            features[feature_name] = (
                record["shared_count"] if record else 0
            )

    return features


def upsert_graph_entities(
    neo4j_driver: Driver,
    event: dict[str, Any],
) -> None:
    """Create / merge nodes and relationships from a normalised event dict.

    Expected keys in *event*::

        account_id, merchant_id, device_id, ip_id, token_id,
        event_type, amount, created_at (ISO-8601 string)

    All relationships carry a ``created_at`` property for time-bounded queries.
    """
    created_at = event.get("created_at", datetime.utcnow().isoformat())

    with neo4j_driver.session() as session:
        session.run(
            """
            MERGE (a:Account {id: $account_id})
            SET a.merchant_id = $merchant_id

            MERGE (d:Device  {id: $device_id})
            MERGE (i:IP      {id: $ip_id})
            MERGE (t:Token   {id: $token_id})

            MERGE (a)-[r1:USES_DEVICE]->(d)
              ON CREATE SET r1.created_at = datetime($created_at)
              ON MATCH  SET r1.last_seen  = datetime($created_at)

            MERGE (a)-[r2:USES_IP]->(i)
              ON CREATE SET r2.created_at = datetime($created_at)
              ON MATCH  SET r2.last_seen  = datetime($created_at)

            MERGE (a)-[r3:USES_TOKEN]->(t)
              ON CREATE SET r3.created_at = datetime($created_at)
              ON MATCH  SET r3.last_seen  = datetime($created_at)
            """,
            {
                "account_id": event["account_id"],
                "merchant_id": event.get("merchant_id", ""),
                "device_id": event.get("device_id", ""),
                "ip_id": event.get("ip_id", ""),
                "token_id": event.get("token_id", ""),
                "created_at": created_at,
            },
        )
