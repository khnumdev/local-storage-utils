from __future__ import annotations

import json
from typing import List, Optional
from typing import Annotated

import typer

from gcd_tools.config import AppConfig, load_config
from gcd_tools.analyze_kinds import analyze_kinds, print_summary_table
from gcd_tools.analyze_entity_fields import analyze_field_contributions, print_field_summary
from gcd_tools.cleanup_expired import cleanup_expired

app = typer.Typer(help="Utilities for analyzing and managing local Datastore/Firestore (Datastore mode)")

# Reusable option aliases
ConfigOpt = Annotated[Optional[str], typer.Option(None, "--config", help="Path to config.yaml")]
ProjectOpt = Annotated[Optional[str], typer.Option(None, "--project", help="GCP/Emulator project id")]
EmulatorHostOpt = Annotated[
    Optional[str], typer.Option(None, "--emulator-host", help="Emulator host, e.g. localhost:8010")
]
LogLevelOpt = Annotated[Optional[str], typer.Option(None, "--log-level", help="Logging level")]
NamespacesOpt = Annotated[
    Optional[List[str]],
    typer.Option(None, "--namespace", "-n", help="Namespaces to process (omit to process all)"),
]
KindsOpt = Annotated[
    Optional[List[str]],
    typer.Option(
        None, "--kind", "-k", help="Kinds to process (omit to process all in each namespace)"
    ),
]
SingleNamespaceOpt = Annotated[
    Optional[str], typer.Option(None, "--namespace", "-n", help="Namespace to query (omit to use all)")
]
SingleKindOpt = Annotated[
    Optional[str], typer.Option(None, "--kind", "-k", help="Kind to analyze (falls back to config.kind)")
]


def _load_cfg(
    config_path: Optional[str],
    project: Optional[str],
    emulator_host: Optional[str],
    log_level: Optional[str],
) -> AppConfig:
    overrides = {}
    if project:
        overrides["project_id"] = project
    if emulator_host:
        overrides["emulator_host"] = emulator_host
    if log_level:
        overrides["log_level"] = log_level
    return load_config(config_path, overrides)


@app.command("analyze-kinds")
def cmd_analyze_kinds(
    config: ConfigOpt,
    project: ProjectOpt,
    emulator_host: EmulatorHostOpt,
    log_level: LogLevelOpt,
    namespace: NamespacesOpt,
    kind: KindsOpt,
    output: Optional[str] = typer.Option(None, help="Output CSV file path"),
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    if namespace:
        cfg.namespaces = list(namespace)
    if kind:
        cfg.kinds = list(kind)

    rows = analyze_kinds(cfg)
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write("namespace,kind,count,size,bytes\n")
            for r in rows:
                ns = r.get("namespace") or ""
                fh.write(f"{ns},{r['kind']},{r['count']},{r['size']},{r['bytes']}\n")
        typer.echo(f"Wrote {len(rows)} rows to {output}")
    else:
        print_summary_table(rows)


@app.command("analyze-fields")
def cmd_analyze_fields(
    kind: SingleKindOpt,
    namespace: SingleNamespaceOpt,
    group_by: Annotated[Optional[str], typer.Option(None, help="Group results by this field value (falls back to config.group_by_field)")],
    only_field: Annotated[Optional[List[str]], typer.Option(None, "--only-field", help="Only consider these fields")],
    config: ConfigOpt,
    project: ProjectOpt,
    emulator_host: EmulatorHostOpt,
    log_level: LogLevelOpt,
    output_json: Annotated[Optional[str], typer.Option(None, help="Write raw JSON results to file")],
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    target_kind = kind or cfg.kind
    target_namespace = namespace if namespace is not None else cfg.namespace
    group_by_field = group_by if group_by is not None else cfg.group_by_field

    if not target_kind:
        raise typer.BadParameter("--kind is required (either via flag or config.kind)")

    result = analyze_field_contributions(
        cfg,
        kind=target_kind,
        namespace=target_namespace,
        group_by_field=group_by_field,
        only_fields=list(only_field) if only_field else None,
    )

    if output_json:
        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        typer.echo(f"Wrote JSON results to {output_json}")
    else:
        print_field_summary(result)


@app.command("cleanup")
def cmd_cleanup(
    config: ConfigOpt,
    project: ProjectOpt,
    emulator_host: EmulatorHostOpt,
    log_level: LogLevelOpt,
    namespace: NamespacesOpt,
    kind: KindsOpt,
    ttl_field: Annotated[Optional[str], typer.Option(None, help="TTL field name (falls back to config.ttl_field)")],
    delete_missing_ttl: Annotated[
        Optional[bool],
        typer.Option(None, help="Delete when TTL field is missing (falls back to config.delete_missing_ttl)"),
    ],
    batch_size: Annotated[Optional[int], typer.Option(None, help="Delete batch size (falls back to config.batch_size)")],
    dry_run: Annotated[bool, typer.Option(False, help="Only report counts; do not delete")],
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    if namespace:
        cfg.namespaces = list(namespace)
    if kind:
        cfg.kinds = list(kind)
    if ttl_field is not None:
        cfg.ttl_field = ttl_field
    if delete_missing_ttl is not None:
        cfg.delete_missing_ttl = delete_missing_ttl
    if batch_size is not None:
        cfg.batch_size = batch_size

    totals = cleanup_expired(cfg, dry_run=dry_run)
    deleted_sum = sum(totals.values())
    typer.echo(f"Total entities {'to delete' if dry_run else 'deleted'}: {deleted_sum}")


if __name__ == "__main__":
    app()