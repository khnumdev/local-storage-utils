from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from google.cloud import datastore
from google.cloud.datastore.helpers import entity_to_protobuf

from .config import (
    AppConfig,
    build_client,
    list_namespaces,
    list_kinds,
    format_size,
)

logger = logging.getLogger(__name__)


def get_kind_stats(client, kind: str, namespace: Optional[str] = None) -> Tuple[Optional[int], Optional[int]]:
    """
    Returns (count, bytes) for the given kind/namespace using Datastore statistics.
    Falls back to None if not found.
    """
    if namespace:
        stats_kind = "__Stat_Kind_Ns__"
        query = client.query(kind=stats_kind)
        query.add_filter("kind_name", "=", kind)
        query.add_filter("namespace_name", "=", namespace)
    else:
        stats_kind = "__Stat_Kind__"
        query = client.query(kind=stats_kind)
        query.add_filter("kind_name", "=", kind)

    results = list(query.fetch(limit=1))
    if results:
        return results[0]["count"], results[0]["bytes"]
    return None, None


def estimate_entity_count_and_size(client, kind: str, namespace: Optional[str], sample_size: int = 100) -> Tuple[int, int]:
    """
    Original keys-only method: exact count, approximate bytes via sampling.
    """
    # Count with keys-only
    count_query = client.query(kind=kind, namespace=namespace or None)
    count_query.keys_only()
    total_count = sum(1 for _ in count_query.fetch())

    # Sample for size
    sample_query = client.query(kind=kind, namespace=namespace or None)
    sample_entities = list(sample_query.fetch(limit=sample_size))
    if sample_entities:
        avg_size = sum(len(entity_to_protobuf(e)._pb.SerializeToString()) for e in sample_entities) / len(sample_entities)
    else:
        avg_size = 0

    return total_count, int(avg_size * total_count)


def analyze_kinds(config: AppConfig, method: Optional[str] = None) -> List[Dict]:
    """
    Analyze kinds using either:
      - 'stats' (default) => fast built-in Datastore statistics
      - 'scan'            => keys-only scan with sampling
    Falls back to 'scan' if stats are missing for a kind.
    """
    client = build_client(config)

    # Decide method priority: parameter > config > default
    method = method or getattr(config, "method", None) or "stats"

    # Thanks to config.py normalisation, [] is the only “all” case
    namespaces = config.namespaces or list_namespaces(client)

    from tqdm import tqdm
    results: List[Dict] = []
    for ns in namespaces:
        kinds = config.kinds or list_kinds(client, ns)
        logger.info("Analyzing namespace=%s, %d kinds", ns or "(default)", len(kinds))
        for kind in tqdm(kinds, desc=f"Analyzing kinds in ns={ns or '(default)'}", unit="kind"):
            if method == "stats":
                count, total_bytes = get_kind_stats(client, kind, ns)
                if count is None:
                    logger.warning("Stats not found for kind=%s, ns=%s — falling back to scan", kind, ns or "(default)")
                    count, total_bytes = estimate_entity_count_and_size(client, kind, ns)
            elif method == "scan":
                count, total_bytes = estimate_entity_count_and_size(client, kind, ns)
            else:
                raise ValueError(f"Unknown method: {method}")

            results.append(
                {
                    "namespace": ns,
                    "kind": kind,
                    "count": count,
                    "bytes": total_bytes,
                    "size": format_size(total_bytes),
                }
            )
    return results


def print_summary_table(rows: List[Dict]) -> None:
    # Plain stdout table for wide compatibility
    print("namespace,kind,count,size,bytes")
    for r in rows:
        ns = r.get("namespace") or ""
        print(f"{ns},{r['kind']},{r['count']},{r['size']},{r['bytes']}")
