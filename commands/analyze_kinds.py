from __future__ import annotations

import logging
from typing import Dict, List

from google.cloud.datastore.helpers import entity_to_protobuf

from .config import (
    AppConfig,
    build_client,
    list_namespaces,
    list_kinds,
    format_size,
)

logger = logging.getLogger(__name__)


def get_kind_stats(client, kind: str, namespace: str | None = None) -> tuple[int | None, int | None]:
    """
    Returns (count, bytes) for the given kind/namespace using Datastore statistics.
    Falls back to None if not found.
    """
    if namespace:
        stats_kind = "__Stat_Kind_Ns__"
        query = client.query(kind=stats_kind)
        # prefer keyword-style filter to avoid positional-arg deprecation warnings
        query.add_filter(filter=("kind_name", "=", kind))
        query.add_filter(filter=("namespace_name", "=", namespace))
    else:
        stats_kind = "__Stat_Kind__"
        query = client.query(kind=stats_kind)
        query.add_filter(filter=("kind_name", "=", kind))

    results = list(query.fetch(limit=1))
    if results:
        return results[0]["count"], results[0]["bytes"]
    return None, None


def estimate_entity_count_and_size(client, kind: str, namespace: str | None, sample_size: int = 100) -> tuple[int, int]:
    """
    Original keys-only method: exact count, approximate bytes via sampling.
    """
    # Count with keys-only
    count_query = client.query(kind=kind, namespace=namespace or None)
    count_query.keys_only()
    # Iterate pages to avoid building large lists in memory
    total_count = 0
    it = count_query.fetch()
    for page in it.pages:
        # each page is an iterator of entities (keys-only), count them
        page_count = sum(1 for _ in page)
        total_count += page_count

    # Sample for size
    sample_query = client.query(kind=kind, namespace=namespace or None)
    sample_entities = list(sample_query.fetch(limit=sample_size))
    if sample_entities:
        avg_size = sum(len(entity_to_protobuf(e)._pb.SerializeToString()) for e in sample_entities) / len(sample_entities)
    else:
        avg_size = 0

    return total_count, int(avg_size * total_count)


def analyze_kinds(config: AppConfig, method: str | None = None) -> List[Dict]:
    """
    Analyze kinds using either:
      - 'stats' (default) => fast built-in Datastore statistics
      - 'scan'            => keys-only scan with sampling
    Falls back to 'scan' if stats are missing for a kind.
    """
    client = build_client(config)

    # Decide method priority: parameter > config > default
    method = method or getattr(config, "method", None) or "stats"

    # If namespaces is None or empty, iterate all available namespaces
    if not config.namespaces:
        namespaces = list_namespaces(client)
    else:
        namespaces = config.namespaces

    print(f"Found namespaces: {namespaces}")
    from tqdm import tqdm
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: List[Dict] = []
    for ns in namespaces:
        kinds = config.kinds or list_kinds(client, ns)
        print(f"Namespace '{ns}': found kinds: {kinds}")
        logger.info("Analyzing namespace=%s, %d kinds", ns or "(default)", len(kinds))

        # Parallelize per-kind work (bounded pool)
        max_workers = min(8, max(1, len(kinds)))
        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = {}

            def _process_kind(k):
                if method == "stats":
                    count, total_bytes = get_kind_stats(client, k, ns)
                    if count is None:
                        logger.warning("Stats not found for kind=%s, ns=%s — falling back to scan", k, ns or "(default)")
                        count, total_bytes = estimate_entity_count_and_size(client, k, ns)
                elif method == "scan":
                    count, total_bytes = estimate_entity_count_and_size(client, k, ns)
                else:
                    raise ValueError(f"Unknown method: {method}")

                return {
                    "namespace": ns,
                    "kind": k,
                    "count": count,
                    "bytes": total_bytes,
                    "size": format_size(total_bytes),
                }

            for k in kinds:
                futures[exe.submit(_process_kind, k)] = k

            # Show progress as futures complete
            for fut in tqdm(as_completed(futures), total=len(futures), desc=f"Analyzing kinds in ns={ns or '(default)'}", unit="kind"):
                res = fut.result()
                results.append(res)
    return results


def print_summary_table(rows: List[Dict]) -> None:
    # Plain stdout table for wide compatibility
    print("namespace,kind,count,size,bytes")
    for r in rows:
        ns = r.get("namespace") or ""
        print(f"{ns},{r['kind']},{r['count']},{r['size']},{r['bytes']}")
