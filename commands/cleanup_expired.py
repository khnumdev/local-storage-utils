from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

from google.cloud import datastore

from .config import (
    AppConfig,
    build_client,
    list_namespaces,
    list_kinds,
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

    # If namespaces is None or empty, iterate all available namespaces
    if not config.namespaces:
        namespaces = list_namespaces(client)
    else:
        namespaces = config.namespaces

    totals: Dict[str, int] = {}
    now = datetime.now(timezone.utc)

    for ns in namespaces:
        # Determine kinds: explicit list, or all in namespace
        kinds = config.kinds if config.kinds else list_kinds(client, ns)

        for kind in kinds:
            # Use projection to fetch only the TTL field and key to reduce payload
            query = client.query(kind=kind, namespace=ns or None)
            try:
                query.projection = [config.ttl_field]
            except Exception:
                # older client versions may not support projection assignment; ignore
                pass

            to_delete: List[datastore.Key] = []
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
                    except Exception:
                        # If unparsable or timezone-less, skip
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
                    # Prepare batches
                    batches = list(chunked(to_delete, config.batch_size))
                    # Parallelize deletion of batches; keep max workers modest to avoid overwhelming emulator
                    from concurrent.futures import ThreadPoolExecutor, as_completed

                    max_workers = min(8, max(1, len(batches)))
                    with ThreadPoolExecutor(max_workers=max_workers) as exe:
                        futures = {exe.submit(client.delete_multi, list(b)): b for b in batches}
                        for fut in tqdm(as_completed(futures), total=len(futures), desc=f"Deleting {kind} in ns={ns or '(default)'}", unit="batch"):
                            # ensure any exceptions bubble
                            fut.result()
                            deleted += len(futures[fut])
                logger.info(
                    "ns=%s kind=%s deleted %d expired entities",
                    ns or "(default)",
                    kind,
                    deleted,
                )
                totals[f"{ns}:{kind}"] = deleted

    return totals
