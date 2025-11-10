from __future__ import annotations

import json
from typing import List, Optional, Annotated

import typer

from commands.config import AppConfig, load_config
from commands.analyze_kinds import analyze_kinds, print_summary_table
from commands.analyze_entity_fields import analyze_field_contributions, print_field_summary
from commands.cleanup_expired import cleanup_expired
from commands.drive_sync import push_to_drive, pull_from_drive

app = typer.Typer(
    help="Utilities for analyzing and managing local Datastore/Firestore (Datastore mode)",
    no_args_is_help=True,
)

# Aliases with flags only — no defaults here
ConfigOpt = Annotated[Optional[str], typer.Option("--config", help="Path to config.yaml")]
ProjectOpt = Annotated[Optional[str], typer.Option("--project", help="GCP/Emulator project id")]
EmulatorHostOpt = Annotated[
    Optional[str], typer.Option("--emulator-host", help="Emulator host, e.g. localhost:8010")
]
LogLevelOpt = Annotated[Optional[str], typer.Option("--log-level", help="Logging level")]
KindsOpt = Annotated[
    Optional[List[str]],
    typer.Option(
        "--kind", "-k", help="Kinds to process (omit or empty to process all in each namespace)"
    ),
]
SingleKindOpt = Annotated[
    Optional[str], typer.Option("--kind", "-k", help="Kind to analyze (falls back to config.kind)")
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
    config: ConfigOpt = None,
    project: ProjectOpt = None,
    emulator_host: EmulatorHostOpt = None,
    log_level: LogLevelOpt = None,
    kind: KindsOpt = None,
    output: Annotated[Optional[str], typer.Option("--output", help="Output CSV file path")] = None,
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    if kind is not None:
        # Normalise: treat [""] as empty (all kinds)
        cfg.kinds = [k for k in kind if k]  # drop empty strings
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
    kind: SingleKindOpt = None,
    namespace: Annotated[
        Optional[str],
        typer.Option("--namespace", "-n", help="Namespace to query (omit to use all)"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option(
            "--group-by",
            help="Group results by this field value (falls back to config.group_by_field)",
        ),
    ] = None,
    only_field: Annotated[
        Optional[List[str]], typer.Option("--only-field", help="Only consider these fields")
    ] = None,
    config: ConfigOpt = None,
    project: ProjectOpt = None,
    emulator_host: EmulatorHostOpt = None,
    log_level: LogLevelOpt = None,
    output_json: Annotated[
        Optional[str], typer.Option("--output-json", help="Write raw JSON results to file")
    ] = None,
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
        only_fields=[f for f in only_field] if only_field else None,
    )

    if output_json:
        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        typer.echo(f"Wrote JSON results to {output_json}")
    else:
        print_field_summary(result)


@app.command("cleanup")
def cmd_cleanup(
    config: ConfigOpt = None,
    project: ProjectOpt = None,
    emulator_host: EmulatorHostOpt = None,
    log_level: LogLevelOpt = None,
    kind: KindsOpt = None,
    ttl_field: Annotated[
        Optional[str],
        typer.Option("--ttl-field", help="TTL field name (falls back to config.ttl_field)"),
    ] = None,
    delete_missing_ttl: Annotated[
        Optional[bool],
        typer.Option(
            "--delete-missing-ttl",
            help="Delete when TTL field is missing (falls back to config.delete_missing_ttl)",
        ),
    ] = None,
    batch_size: Annotated[
        Optional[int],
        typer.Option("--batch-size", help="Delete batch size (falls back to config.batch_size)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Only report counts; do not delete")
    ] = False,
):
    cfg = _load_cfg(config, project, emulator_host, log_level)

    if kind is not None:
        cfg.kinds = [k for k in kind if k]
    if ttl_field is not None:
        cfg.ttl_field = ttl_field
    if delete_missing_ttl is not None:
        cfg.delete_missing_ttl = delete_missing_ttl
    if batch_size is not None:
        cfg.batch_size = batch_size

    totals = cleanup_expired(cfg, dry_run=dry_run)
    deleted_sum = sum(totals.values())
    typer.echo(f"Total entities {'to delete' if dry_run else 'deleted'}: {deleted_sum}")


db_app = typer.Typer(help="Database backup management commands", no_args_is_help=True)


@db_app.command("push")
def db_push(
    version: Annotated[
        Optional[str], typer.Argument(help="Version name (defaults to today's date YYYY-mm-DD)")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("-o", "--overwrite", help="Overwrite existing file with same name")
    ] = False,
    local_db: Annotated[
        Optional[str],
        typer.Option(
            "--local-db", help="Path to local-db binary (falls back to config.local_db_path)"
        ),
    ] = None,
    config: ConfigOpt = None,
    log_level: LogLevelOpt = None,
):
    cfg = _load_cfg(config, None, None, log_level)
    push_to_drive(cfg, version, overwrite, local_db)


@db_app.command("pull")
def db_pull(
    version: Annotated[
        Optional[str], typer.Argument(help="Version name (omit to download latest)")
    ] = None,
    local_db: Annotated[
        Optional[str],
        typer.Option(
            "--local-db", help="Path to local-db binary (falls back to config.local_db_path)"
        ),
    ] = None,
    config: ConfigOpt = None,
    log_level: LogLevelOpt = None,
):
    cfg = _load_cfg(config, None, None, log_level)
    pull_from_drive(cfg, version, local_db)


app.add_typer(db_app, name="db")


if __name__ == "__main__":
    import sys

    # If invoked with no subcommand/arguments, show help (list available commands/options)
    if len(sys.argv) == 1:
        # append --help so Typer/Click prints the global help instead of raising Missing command
        sys.argv.append("--help")

    app()
