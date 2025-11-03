# local-storage-utils

[![CI](https://github.com/khnumdev/local-storage-utils/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/khnumdev/local-storage-utils/actions/workflows/ci.yml)
[![Build](https://github.com/khnumdev/local-storage-utils/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/khnumdev/local-storage-utils/actions/workflows/build.yml)
[![Release](https://github.com/khnumdev/local-storage-utils/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/khnumdev/local-storage-utils/actions/workflows/release.yml)

Utilities for analyzing and managing local Datastore/Firestore (Datastore mode) data. Works with both the Datastore Emulator and GCP using Application Default Credentials.

## Install (PyPI)

```bash
pip install local-storage-utils
```

This installs the `lsu` CLI.

Installing from TestPyPI (for dry-runs)
-------------------------------------

If you want to test publishing to TestPyPI and install the package from the test index, prefer doing that inside a virtual environment. This avoids the "externally-managed-environment" / PEP 668 error you saw when trying to install system-wide on Debian/Ubuntu.

Recommended steps:

```bash
# create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# upgrade pip in the venv
python -m pip install --upgrade pip

# install from TestPyPI; use --extra-index-url so runtime dependencies are resolved from the real PyPI
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple local-storage-utils
```

Notes:
- The error "externally-managed-environment" happens when pip is blocked from modifying a system Python managed by the OS (PEP 668). The recommended fix is to use a virtual environment or pipx — do not use `--break-system-packages` unless you understand the risks.
- If you prefer `pipx` for isolated CLI installs, use `pipx install` inside a separate environment or consult pipx docs for installing from alternate indexes.

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

Example `config.yaml` (full example with comments):

```yaml
# Project / environment
project_id: "my-project"          # (string) GCP project id. If omitted, ADC or DATASTORE_PROJECT_ID env var will be used.
emulator_host: "localhost:8010"   # (string) Datastore emulator host (host:port). If set, the emulator path is used.

# Explicit filters (empty -> iterate all)
namespaces: [""]                   # (list) Namespaces to include. [""] means include default namespace and allow discovery of others.
kinds: []                            # (list) Kinds to include. Empty/omit means discover all kinds per namespace.

# Defaults used by some commands (optional)
kind: ""                            # (string) Default kind used by analyze-fields when CLI --kind is not provided.
namespace: ""                       # (string) Default namespace used when CLI --namespace is omitted.

# Cleanup settings
ttl_field: "expireAt"               # (string) Property name that contains the TTL/expiry timestamp.
delete_missing_ttl: true              # (bool) If true, entities missing the TTL field will be deleted by cleanup.
batch_size: 500                       # (int) Number of keys to delete per batch when running cleanup (tunable).

# Analysis settings
group_by_field: null                  # (string|null) Field name to group analysis by (e.g., batchId). Null means no grouping.
sample_size: 500                      # (int) Max entities to sample per-kind/per-group to bound analysis work. Set 0 or null to disable sampling.
enable_parallel: true                 # (bool) Enable multi-threaded processing for analysis and deletion. Set false to force single-threaded.

# Logging
log_level: "INFO"                   # (string) Logging level (DEBUG, INFO, WARNING, ERROR).
```

The keys above map directly to CLI flags (CLI flags override values in `config.yaml`). Omit any option to use sensible defaults.

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

Publishing
-------

This project uses the `release` workflow to publish releases to PyPI. Follow the packaging tutorial for a complete guide on packaging and publishing: https://packaging.python.org/en/latest/tutorials/packaging-projects/

We support publishing to either TestPyPI (for dry runs) or the real PyPI. The workflow can be triggered automatically on pushes to `main` or manually via the Actions UI (use the "Run workflow" button). When you run it manually you can set the `publish_target` input to `testpypi` to publish to TestPyPI instead of PyPI.

Secrets and tokens
- For production publishing to the real PyPI, set the repository secret named `PYPI_API_TOKEN` with a PyPI API token.
- For test publishing to TestPyPI, set the repository secret named `TEST_PYPI_API_TOKEN` with a TestPyPI API token.

The release workflow selects the appropriate token based on the `publish_target` input. Use TestPyPI first to validate packaging and metadata before publishing to the real index.

Notes
- `sample_size` bounds per-kind/group analysis to avoid scanning entire datasets. Set to 0 or `null` in config to disable sampling.
- `enable_parallel` (default true) enables multi-threaded processing during analysis and deletion; set to false to force single-threaded behavior.

If you'd like a short walkthrough or to change the default Makefile targets, tell me what you'd prefer and I can adjust the README or Makefile.
pip install ruff black
