from __future__ import annotations

import json
from typing import List, Optional

import typer

from gcd_tools.config import AppConfig, load_config, format_size
from gcd_tools.analyze_kinds import analyze_kinds, print_summary_table
from gcd_tools.analyze_entity_fields import analyze_field_contributions, print_field_summary
from gcd_tools.cleanup_expired import cleanup_expired

app = typer.Typer(help="Utilities for analyzing and managing local Datastore/Firestore (Datastore mode)")


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
    config: Optional[str] = typer.Option(None, help="Path to config.yaml"),
    project: Optional[str] = typer.Option(None, help="GCP/Emulator project id"),
    emulator_host: Optional[str] = typer.Option(None, help="Emulator host, e.g. localhost:8010"),
    log_level: Optional[str] = typer.Option(None, help="Logging level"),
    namespace: Optional[List[str]] = typer.Option(None, "--namespace", "-n", help="Namespaces to include"),
    exclude_namespace: Optional[List[str]] = typer.Option(None, "--exclude-namespace", help="Namespaces to exclude"),
    kind: Optional[List[str]] = typer.Option(None, "--kind", "-k", help="Kinds to include"),
    exclude_kind: Optional[List[str]] = typer.Option(None, "--exclude-kind", help="Kinds to exclude"),
    output: Optional[str] = typer.Option(None, help="Output CSV file path"),
):
    cfg = _load_cfg(config, project, emulator_host, log_level)
    if namespace:
        cfg.namespace_include = list(namespace)
    if exclude_namespace:
        cfg.namespace_exclude = list(exclude_namespace)
    if kind:
        cfg.kinds_include = list(kind)
    if exclude_kind:
        cfg.kinds_exclude = list(exclude_kind)

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
    kind: str = typer.Option(..., "--kind", "-k", help="Kind to analyze"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace to query"),
    group_by: Optional[str] = typer.Option(None, help="Group results by this field value"),
    only_field: Optional[List[str]] = typer.Option(None, "--only-field", help="Only consider these fields"),
    config: Optional[str] = typer.Option(None, help="Path to config.yaml"),
    project: Optional[str] = typer.Option(None, help="GCP/Emulator project id"),
    emulator_host: Optional[str] = typer.Option(None, help="Emulator host, e.g. localhost:8010"),
    log_level: Optional[str] = typer.Option(None, help="Logging level"),
    output_json: Optional[str] = typer.Option(None, help="Write raw JSON results to file"),
):
    cfg = _load_cfg(config, project, emulator_host, log_level)
    result = analyze_field_contributions(
        cfg, kind=kind, namespace=namespace, group_by_field=group_by, only_fields=list(only_field) if only_field else None
    )

    if output_json:
        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        typer.echo(f"Wrote JSON results to {output_json}")
    else:
        print_field_summary(result)


@app.command("cleanup")
def cmd_cleanup(
    config: Optional[str] = typer.Option(None, help="Path to config.yaml"),
    project: Optional[str] = typer.Option(None, help="GCP/Emulator project id"),
    emulator_host: Optional[str] = typer.Option(None, help="Emulator host, e.g. localhost:8010"),
    log_level: Optional[str] = typer.Option(None, help="Logging level"),
    namespace: Optional[List[str]] = typer.Option(None, "--namespace", "-n", help="Namespaces to include"),
    exclude_namespace: Optional[List[str]] = typer.Option(None, "--exclude-namespace", help="Namespaces to exclude"),
    kind: Optional[List[str]] = typer.Option(None, "--kind", "-k", help="Kinds to include"),
    exclude_kind: Optional[List[str]] = typer.Option(None, "--exclude-kind", help="Kinds to exclude"),
    ttl_field: Optional[str] = typer.Option(None, help="TTL field name"),
    delete_missing_ttl: bool = typer.Option(True, help="Delete when TTL field is missing"),
    batch_size: Optional[int] = typer.Option(None, help="Delete batch size"),
    dry_run: bool = typer.Option(False, help="Only report counts; do not delete"),
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    if namespace:
        cfg.namespace_include = list(namespace)
    if exclude_namespace:
        cfg.namespace_exclude = list(exclude_namespace)
    if kind:
        cfg.kinds_include = list(kind)
    if exclude_kind:
        cfg.kinds_exclude = list(exclude_kind)
    if ttl_field:
        cfg.ttl_field = ttl_field
    cfg.delete_missing_ttl = delete_missing_ttl
    if batch_size:
        cfg.batch_size = batch_size

    totals = cleanup_expired(cfg, dry_run=dry_run)
    deleted_sum = sum(totals.values())
    typer.echo(f"Total entities {'to delete' if dry_run else 'deleted'}: {deleted_sum}")


if __name__ == "__main__":
    app()