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
    sample_size: Optional[int] = 500,
    enable_parallel: bool = True,
) -> Tuple[Dict[str, int], int, int]:
    field_totals: DefaultDict[str, int] = defaultdict(int)
    total_size = 0
    entity_count = 0

    from tqdm import tqdm
    # Convert to iterator and optionally sample first `sample_size` entities to bound work
    from itertools import islice

    it = iter(entities)
    if sample_size and sample_size > 0:
        it = islice(it, sample_size)

    ents = list(it)

    def _process_entity(e: datastore.Entity):
        # Returns (entity_size, {field: contribution, ...})
        proto = entity_to_protobuf(e)._pb
        full_bytes = len(proto.SerializeToString())
        contributions = {}
        for field in (target_fields or list(e.keys())):
            if field not in e:
                continue
            reduced_entity = _clone_without_field(e, field)
            reduced_size = len(entity_to_protobuf(reduced_entity)._pb.SerializeToString())
            contributions[field] = max(0, full_bytes - reduced_size)
        return full_bytes, contributions

    if enable_parallel:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results_iter = []
        with ThreadPoolExecutor(max_workers=8) as exe:
            futures = {exe.submit(_process_entity, e): e for e in ents}
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Analyzing field contributions", unit="entity"):
                entity_count += 1
                full_size, contributions = fut.result()
                total_size += full_size
                for f, v in contributions.items():
                    field_totals[f] += v
    else:
        for entity in tqdm(ents, desc="Analyzing field contributions", unit="entity"):
            entity_count += 1
            full_size, contributions = _process_entity(entity)
            total_size += full_size
            for f, v in contributions.items():
                field_totals[f] += v

    return dict(field_totals), total_size, entity_count


def _analyze_single_namespace(
    client: datastore.Client,
    kind: str,
    namespace: Optional[str],
    group_by_field: Optional[str],
    only_fields: Optional[List[str]],
    sample_size: Optional[int] = 500,
    enable_parallel: bool = True,
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
                ents, target_fields=only_fields, sample_size=sample_size, enable_parallel=enable_parallel
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
        query.fetch(), target_fields=only_fields, sample_size=sample_size, enable_parallel=enable_parallel
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

    # sample_size can be set in config to bound per-kind work for large datasets
    sample_size = getattr(config, "sample_size", 500)
    enable_parallel = getattr(config, "enable_parallel", True)

    # If no namespace provided, or config.namespaces is None/empty, iterate all namespaces
    if namespace is None:
        if hasattr(config, "namespaces") and (not config.namespaces):
            ns_list = list_namespaces(client)
        else:
            ns_list = [namespace] if namespace else list_namespaces(client)
        results: Dict[str, Dict] = {}
        for ns in ns_list:
            results[ns or ""] = _analyze_single_namespace(
                client, kind=kind, namespace=ns, group_by_field=group_by_field, only_fields=only_fields, sample_size=sample_size
            )
            
        return {"by_namespace": results}

    # Single namespace
    return _analyze_single_namespace(
        client, kind=kind, namespace=namespace, group_by_field=group_by_field, only_fields=only_fields, sample_size=sample_size, enable_parallel=enable_parallel
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
