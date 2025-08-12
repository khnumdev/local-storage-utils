from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

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

    # Determine namespaces: explicit list, or all
    namespaces = config.namespaces if config.namespaces else list_namespaces(client)

    totals: Dict[str, int] = {}
    now = datetime.now(timezone.utc)

    for ns in namespaces:
        # Determine kinds: explicit list, or all in namespace
        kinds = config.kinds if config.kinds else list_kinds(client, ns)

        for kind in kinds:
            query = client.query(kind=kind, namespace=ns or None)
            to_delete: List[datastore.Key] = []
            for entity in query.fetch():
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
                deleted = _delete_in_batches(client, to_delete, config.batch_size) if to_delete else 0
                logger.info(
                    "ns=%s kind=%s deleted %d expired entities",
                    ns or "(default)",
                    kind,
                    deleted,
                )
                totals[f"{ns}:{kind}"] = deleted

    return totals