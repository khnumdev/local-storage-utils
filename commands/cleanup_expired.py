from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

from google.cloud import datastore

from .config import (
    AppConfig,
    build_client,
    resolve_namespaces,
    resolve_kinds,
    parallel_map,
    chunked,
)

logger = logging.getLogger(__name__)


def _delete_in_batches(client: datastore.Client, keys: List[datastore.Key], batch_size: int) -> int:
    deleted = 0
    for batch in chunked(keys, batch_size):
        client.delete_multi(batch)  # type: ignore[arg-type]
        deleted += len(batch)
    return deleted


def cleanup_expired(
    config: AppConfig,
    dry_run: bool = False,
) -> Dict[str, int]:
    client = build_client(config)
    namespaces = resolve_namespaces(client, config)

    totals: Dict[str, int] = {}
    now = datetime.now(timezone.utc)

    for ns in namespaces:
        kinds = resolve_kinds(client, config, ns)

        for kind in kinds:
            # Use projection to fetch only the TTL field and key to reduce payload
            query = client.query(kind=kind, namespace=ns or None)
            try:
                query.projection = [config.ttl_field]
            except Exception:
                # older client versions may not support projection assignment; ignore
                pass

            to_delete: List[datastore.Key] = []
            warned_bad_ttl = False
            from tqdm import tqdm
            # Stream entities to avoid holding all in memory and show progress
            it = query.fetch()
            for entity in tqdm(it, desc=f"Scanning {kind} in ns={ns or '(default)'}", unit="entity"):
                # entity may only contain projected fields
                expire_at = entity.get(config.ttl_field)
                expired = expire_at is None if config.delete_missing_ttl else False
                if not expired and expire_at is not None:
                    try:
                        expired = expire_at < now
                    except TypeError:
                        # Naive (tz-less) or otherwise incomparable value; never treated as expired
                        if not warned_bad_ttl:
                            logger.warning(
                                "ns=%s kind=%s: TTL field %r has an incomparable value (e.g. missing timezone) on at least one entity — those entities will never be treated as expired until fixed",
                                ns or "(default)",
                                kind,
                                config.ttl_field,
                            )
                            warned_bad_ttl = True
                        expired = False
                if expired:
                    to_delete.append(entity.key)

            if dry_run:
                logger.info(
                    "[DRY-RUN] ns=%s kind=%s would delete %d entities",
                    ns or "(default)",
                    kind,
                    len(to_delete),
                )
                totals[f"{ns}:{kind}"] = len(to_delete)
            else:
                deleted = 0
                if to_delete:
                    batches = list(chunked(to_delete, config.batch_size))
                    counts = parallel_map(
                        batches,
                        lambda b: (client.delete_multi(list(b)), len(b))[1],
                        desc=f"Deleting {kind} in ns={ns or '(default)'}",
                        unit="batch",
                    )
                    deleted = sum(counts)
                logger.info(
                    "ns=%s kind=%s deleted %d expired entities",
                    ns or "(default)",
                    kind,
                    deleted,
                )
                totals[f"{ns}:{kind}"] = deleted

    return totals
