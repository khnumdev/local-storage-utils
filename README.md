# local-storage-utils

Utilities for analyzing and managing local Datastore/Firestore (Datastore mode) data. Works with both the Datastore Emulator and GCP using Application Default Credentials.

## Install (PyPI)

```bash
pip install local-storage-utils
```

This installs the `lsu` CLI.

## Install (from source)

git clone <this-repo-url>
cd local-storage-utils
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .

### Troubleshooting local installs
- If you see "Command 'python' not found", use `python3 -m venv .venv` (above). Inside the venv, `python` will point to Python 3.
- If you see "externally-managed-environment", you are attempting a system-wide install. Always install into a virtual environment:
  - Create a venv: `python3 -m venv .venv && source .venv/bin/activate`
  - Then use the venv pip: `python -m pip install -U pip && pip install -e .`
  ```bash
  sudo apt-get update && sudo apt-get install -y python3-venv
  ```

## Configuration

- Create a local `config.yaml` in your working directory. It is gitignored and not included in the repo.
- Any CLI flag overrides values from `config.yaml`.
- If neither config nor flags provide a value, the tool falls back to environment variables (for emulator detection) or sensible defaults.

Example `config.yaml`:

```yaml
project_id: "my-project"          # If omitted, ADC/env will be used
emulator_host: "localhost:8010"   # If set, uses Datastore Emulator

# Explicit filters (empty means all)
namespaces: [""]                   # Empty -> iterate all namespaces (including default "")
kinds: []                          # Empty -> iterate all kinds per namespace

 # local-storage-utils — Quickstart

 Lightweight utilities for analyzing and cleaning Datastore (Firestore in Datastore mode). Works with the
 Datastore emulator for local integration testing or GCP when using Application Default Credentials.

 Quick overview
 - CLI: run commands via `python3 cli.py <command>` (or install the package and use the entrypoint).
 - Makefile: convenience targets are provided to create a venv, install deps, and run tests locally.

 Quickstart (from source)
```bash
git clone <this-repo-url>
cd local-storage-utils
# create a venv and install the package in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Makefile shortcuts
 - `make venv` — create `.venv` and install package in editable mode
 - `make unit` — run fast unit tests
 - `make integration` — run integration tests (starts/seeds emulator when configured)

Use these targets to get a working dev environment quickly.

Basic CLI examples
```bash
# list kinds (scans stats or samples)
python3 cli.py analyze-kinds --project my-project

# analyze fields for a kind
python3 cli.py analyze-fields --kind MyKind --group-by batchId

# dry-run cleanup sample
python3 cli.py cleanup --ttl-field expireAt --dry-run
```

Configuration
- Local `config.yaml` is supported; CLI flags override config values.
- Example keys: `project_id`, `emulator_host`, `namespaces`, `kinds`, `kind`, `ttl_field`, `batch_size`, `sample_size`, `enable_parallel`.

Emulator & integration testing
- Start & seed emulator locally:
  - `./scripts/run_emulator_local.sh` (prefers `.venv/bin/python` to run seeder)
  - `./scripts/run_emulator_local.sh --no-seed` to skip seeding
- The seeder accepts `SEED_COUNT` and `SEED_NS_COUNT` env vars to increase dataset size for perf tests.

Run integration tests:
```bash
# create venv and install deps (see Quickstart), then:
make integration
```

Development & tests
- Run unit tests:
  - `make unit` (fast)
- Run full test suite locally:
  - `make integration`

Notes
- `sample_size` bounds per-kind/group analysis to avoid scanning entire datasets. Set to 0 or `null` in config to disable sampling.
- `enable_parallel` (default true) enables multi-threaded processing during analysis and deletion; set to false to force single-threaded behavior.

If you'd like a short walkthrough or to change the default Makefile targets, tell me what you'd prefer and I can adjust the README or Makefile.
pip install ruff black
