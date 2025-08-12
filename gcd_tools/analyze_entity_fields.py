from __future__ import annotations

import logging
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple

from google.cloud import datastore
from google.cloud.datastore.helpers import entity_to_protobuf

from .config import AppConfig, build_client, format_size, list_namespaces

logger = logging.getLogger(__name__)


def _clone_without_field(entity: datastore.Entity, exclude_field: str) -> datastore.Entity:
    new_entity = datastore.Entity(key=entity.key)
    for k, v in entity.items():
        if k != exclude_field:
            new_entity[k] = v
    return new_entity


def _estimate_field_contributions(
    entities: Iterable[datastore.Entity],
    target_fields: Optional[List[str]] = None,
) -> Tuple[Dict[str, int], int, int]:
    field_totals: DefaultDict[str, int] = defaultdict(int)
    total_size = 0
    entity_count = 0

    for entity in entities:
        entity_count += 1
        proto = entity_to_protobuf(entity)._pb
        full_size = len(proto.SerializeToString())
        total_size += full_size

        for field in (target_fields or list(entity.keys())):
            if field not in entity:
                continue
            reduced_entity = _clone_without_field(entity, field)
            reduced_size = len(entity_to_protobuf(reduced_entity)._pb.SerializeToString())
            field_totals[field] += max(0, full_size - reduced_size)

    return dict(field_totals), total_size, entity_count


def _analyze_single_namespace(
    client: datastore.Client,
    kind: str,
    namespace: Optional[str],
    group_by_field: Optional[str],
    only_fields: Optional[List[str]],
) -> Dict:
    query = client.query(kind=kind, namespace=namespace or None)

    if group_by_field:
        logger.info(
            "Analyzing field contributions for kind=%s, namespace=%s grouped by %s",
            kind,
            namespace or "(default)",
            group_by_field,
        )
        grouped_entities: DefaultDict[str, List[datastore.Entity]] = defaultdict(list)
        for entity in query.fetch():
            group_val = entity.get(group_by_field)
            key = str(group_val) if group_val is not None else "<missing>"
            grouped_entities[key].append(entity)

        results: Dict[str, Dict] = {}
        for group_key, ents in grouped_entities.items():
            field_totals, total_size, entity_count = _estimate_field_contributions(
                ents, target_fields=only_fields
            )
            results[group_key] = {
                "namespace": namespace,
                "kind": kind,
                "group": group_key,
                "entity_count": entity_count,
                "total_bytes": total_size,
                "total_size": format_size(total_size),
                "fields": {
                    f: {
                        "bytes": b,
                        "avg_per_entity": (b / entity_count) if entity_count else 0.0,
                        "human": format_size(b),
                    }
                    for f, b in sorted(field_totals.items(), key=lambda x: x[1], reverse=True)
                },
            }
        return {"grouped": results}

    # Ungrouped path
    logger.info(
        "Analyzing field contributions for kind=%s, namespace=%s",
        kind,
        namespace or "(default)",
    )
    field_totals, total_size, entity_count = _estimate_field_contributions(
        query.fetch(), target_fields=only_fields
    )
    return {
        "namespace": namespace,
        "kind": kind,
        "entity_count": entity_count,
        "total_bytes": total_size,
        "total_size": format_size(total_size),
        "fields": {
            f: {
                "bytes": b,
                "avg_per_entity": (b / entity_count) if entity_count else 0.0,
                "human": format_size(b),
            }
            for f, b in sorted(field_totals.items(), key=lambda x: x[1], reverse=True)
        },
    }


def analyze_field_contributions(
    config: AppConfig,
    kind: str,
    namespace: Optional[str] = None,
    group_by_field: Optional[str] = None,
    only_fields: Optional[List[str]] = None,
) -> Dict:
    client = build_client(config)

    # If no namespace provided, iterate across all namespaces
    if namespace is None:
        results: Dict[str, Dict] = {}
        for ns in list_namespaces(client):
            results[ns or ""] = _analyze_single_namespace(
                client, kind=kind, namespace=ns, group_by_field=group_by_field, only_fields=only_fields
            )
        return {"by_namespace": results}

    # Single namespace
    return _analyze_single_namespace(
        client, kind=kind, namespace=namespace, group_by_field=group_by_field, only_fields=only_fields
    )


def print_field_summary(result: Dict) -> None:
    if "by_namespace" in result:
        for ns, data in result["by_namespace"].items():
            print(f"\n=== namespace: {ns or '(default)'} ===")
            print_field_summary(data)
        return

    if "grouped" in result:
        for group_key, data in result["grouped"].items():
            ns = data.get("namespace") or ""
            print(f"\n[group={group_key}] ns={ns} kind={data['kind']} entities={data['entity_count']} total={data['total_size']}")
            for field, stats in data["fields"].items():
                avg = stats["avg_per_entity"]
                print(f"  {field:30} {stats['human']:>12} ({avg:.1f} bytes avg)")
    else:
        ns = result.get("namespace") or ""
        print(
            f"ns={ns} kind={result['kind']} entities={result['entity_count']} total={result['total_size']}"
        )
        for field, stats in result["fields"].items():
            avg = stats["avg_per_entity"]
            print(f"  {field:30} {stats['human']:>12} ({avg:.1f} bytes avg)")