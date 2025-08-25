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

def estimate_entity_count_and_size(
    client: datastore.Client, kind: str, namespace: Optional[str]
) -> Tuple[int, int]:
    query = client.query(kind=kind, namespace=namespace or None)
    total_size = 0
    count = 0
    for entity in query.fetch():
        try:
            raw_proto = entity_to_protobuf(entity)._pb
            total_size += len(raw_proto.SerializeToString())
        except Exception:
            # Fallback: count only
            pass
        count += 1
    return count, total_size

def analyze_kinds(config: AppConfig) -> List[Dict]:
    client = build_client(config)

    # Thanks to config.py normalisation, [] is the only “all” case
    namespaces = config.namespaces or list_namespaces(client)

    results: List[Dict] = []
    for ns in namespaces:
        kinds = config.kinds or list_kinds(client, ns)
        logger.info("Analyzing namespace=%s, %d kinds", ns or "(default)", len(kinds))
        for kind in kinds:
            count, total_bytes = estimate_entity_count_and_size(client, kind, ns)
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
