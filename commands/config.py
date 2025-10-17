from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import yaml
from google.cloud import datastore

@dataclass
class AppConfig:
    project_id: Optional[str] = None
    emulator_host: Optional[str] = None

    # Explicit filters (when empty -> use all)
    namespaces: List[str] = field(default_factory=list)
    kinds: List[str] = field(default_factory=list)

    # Optional defaults for commands that need them (e.g., analyze-fields)
    kind: Optional[str] = None
    namespace: Optional[str] = None

    # Cleanup settings
    ttl_field: str = "expireAt"
    delete_missing_ttl: bool = True
    batch_size: int = 500

    # Analysis settings
    group_by_field: Optional[str] = None

    # Logging
    log_level: str = "INFO"


def _as_list(value: Optional[Iterable[str]]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


def load_config(path: Optional[str] = None, overrides: Optional[Dict] = None) -> AppConfig:
    config = AppConfig()

    # Load YAML if provided or if default exists
    data: Dict = {}
    candidate = path or os.getenv("LSU_CONFIG")
    if not candidate and os.path.exists("config.yaml"):
        candidate = "config.yaml"

    if candidate and os.path.exists(candidate):
        with open(candidate, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    overrides = overrides or {}
    merged = {**data, **overrides}

    config.project_id = merged.get("project_id") or os.getenv("DATASTORE_PROJECT_ID")
    config.emulator_host = merged.get("emulator_host") or os.getenv("DATASTORE_EMULATOR_HOST")

    # Explicit lists (no include/exclude). Empty -> all
    config.namespaces = _as_list(merged.get("namespaces"))
    config.kinds = _as_list(merged.get("kinds"))

    # 🛠 Normalise: treat [""] as empty
    if config.namespaces == [""] or config.namespaces is None:
        config.namespaces = []
    if config.kinds == [""] or config.kinds is None:
        config.kinds = []

    # Optional defaults used by some commands
    config.kind = merged.get("kind")
    config.namespace = merged.get("namespace")

    config.ttl_field = merged.get("ttl_field", config.ttl_field)
    config.delete_missing_ttl = bool(merged.get("delete_missing_ttl", config.delete_missing_ttl))
    config.batch_size = int(merged.get("batch_size", config.batch_size))

    config.group_by_field = merged.get("group_by_field", config.group_by_field)

    config.log_level = str(merged.get("log_level", config.log_level)).upper()

    _configure_logging(config.log_level)
    return config


def _configure_logging(level: str) -> None:
    level_value = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=level_value, format="%(asctime)s | %(levelname)s | %(message)s")


def build_client(config: AppConfig) -> datastore.Client:
    # Prefer explicit emulator_host if provided, otherwise env decides
    if config.emulator_host:
        os.environ["DATASTORE_EMULATOR_HOST"] = config.emulator_host
    # Project id is required in emulator; optional on GCP (ADC will detect)
    if config.project_id:
        os.environ.setdefault("DATASTORE_PROJECT_ID", config.project_id)

    if os.getenv("DATASTORE_EMULATOR_HOST"):
        # When using emulator, ensure a project ID is present
        project_id = os.getenv("DATASTORE_PROJECT_ID") or config.project_id or "local-dev"
        os.environ["DATASTORE_PROJECT_ID"] = project_id
        return datastore.Client(project=project_id)

    # GCP path, relies on ADC if project not provided
    return datastore.Client(project=config.project_id)


def list_namespaces(client: datastore.Client) -> List[str]:
    """
    Return all namespaces in the datastore, including the default ("").
    Always queries __namespace__ in the root context so it works in emulator/GCP.
    """
    # Include default namespace "" first
    namespaces: List[str] = [""]

    # Force namespace=None to query the metadata root
    query = client.query(kind="__namespace__", namespace=None)
    query.keys_only()

    for entity in query.fetch():
        name = entity.key.name or ""
        if name != "":
            namespaces.append(name)

    return namespaces


def list_kinds(client: datastore.Client, namespace: Optional[str]) -> List[str]:
    query = client.query(kind="__kind__", namespace=namespace or None)
    query.keys_only()
    return [e.key.name for e in query.fetch()]


def chunked(iterable: Sequence, chunk_size: int):
    for i in range(0, len(iterable), max(1, chunk_size)):
        yield iterable[i : i + chunk_size]


def format_size(bytes_size: int) -> str:
    size = float(bytes_size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"
