# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`local-storage-utils` (CLI name `lsu`) analyzes and cleans up Google Cloud Datastore / Firestore-in-Datastore-mode data. It targets both the Datastore Emulator (local dev/CI) and real GCP via Application Default Credentials.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
make deps                 # pip install -e .[dev]

# Tests
make unit                 # fast, no emulator needed: tests/test_utils.py tests/test_config.py
make integration           # full suite; tests needing the emulator self-skip if it's unreachable
python -m pytest -q tests/test_config.py::test_load_config_normalizes_namespaces  # single test

# Lint/format
make lint                  # ruff check . && black .

# Run the CLI locally
python cli.py <command> ...          # or: make cli
lsu <command> ...                    # after pip install -e .

# Local emulator for integration testing
./scripts/run_emulator_local.sh              # starts + seeds
./scripts/run_emulator_local.sh --no-seed    # starts without seeding
python scripts/seed_emulator.py              # seed only (SEED_COUNT / SEED_NS_COUNT / SEED_KIND env vars)
```

CI (`.github/workflows/emulator-test.yml`, called from `ci.yml`) runs the real emulator via `gcloud beta emulators datastore` across Python 3.9–3.12, seeds it, then runs `make integration`. Integration tests in `tests/test_commands.py` are written to `pytest.skip(...)` on any exception if the emulator isn't reachable — a passing local `make unit` run does not mean the Datastore-touching code paths were exercised.

## Architecture

- `cli.py` — the only Typer entrypoint (`app`). Each subcommand (`analyze-kinds`, `analyze-fields`, `cleanup`) resolves an `AppConfig` via `_load_cfg`, applies CLI-flag overrides onto whatever the config file/env already set, then calls straight into the corresponding function in `commands/`. There is no other layering — business logic lives in `commands/`, not here.
- `commands/config.py` — shared foundation for everything else:
  - `AppConfig`: a dataclass holding all settings (project/emulator target, namespace/kind filters, cleanup TTL settings, analysis sampling/parallelism, log level).
  - `load_config(path, overrides)`: merge order is **YAML file < env vars (`DATASTORE_PROJECT_ID`, `DATASTORE_EMULATOR_HOST`, `LSU_CONFIG`) < explicit overrides dict**. An empty-string list entry (`[""]`) is normalized to `[]`, and both are treated as "iterate everything" throughout the codebase — this convention (empty/missing filter = all namespaces/kinds) is load-bearing across all three commands, not just a config quirk.
  - `build_client`: decides emulator vs. real GCP purely from whether `DATASTORE_EMULATOR_HOST` ends up set in the environment (it mutates `os.environ` as a side effect of being called — calling it more than once with different configs can leak emulator settings across calls).
  - `list_namespaces` / `list_kinds`: query Datastore's `__namespace__` / `__kind__` metadata kinds directly.
- `commands/analyze_kinds.py` — per-kind count/size. Prefers Datastore's built-in `__Stat_Kind__` / `__Stat_Kind_Ns__` statistics (fast, may be stale/absent), falling back per-kind to a keys-only scan + sampled-size estimate (`estimate_entity_count_and_size`) when stats are missing.
- `commands/analyze_entity_fields.py` — estimates each field's byte contribution to entity size by serializing an entity, then re-serializing a clone with that one field removed and diffing proto sizes (`entity_to_protobuf`). Supports grouping entities by an arbitrary field value (`group_by_field`) and sampling (`sample_size`) to bound cost on large kinds.
- `commands/cleanup_expired.py` — scans a kind with a field projection on `ttl_field` only (to minimize payload), decides expiry by comparing to `datetime.now(timezone.utc)`, and deletes matching keys in parallel batches via `ThreadPoolExecutor` + `client.delete_multi`. Respects `--dry-run` (report only, no deletes).
- All three analysis/cleanup paths independently iterate the same namespace → kind → (parallel work) structure and independently spin up their own `ThreadPoolExecutor`; there's no shared "for each namespace/kind" helper despite the pattern being identical in all three files.

## Conventions worth knowing before editing

- Namespace `""` is the default namespace everywhere; it's displayed as `(default)` in logs/progress bars but stored/compared as `""`.
- CLI flags always take precedence over config file values, which take precedence over env vars baked into `AppConfig` defaults.
- `sample_size: 0` means "no limit" (disables sampling) — not "sample zero entities".
