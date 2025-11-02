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

# Optional defaults
kind: "SourceCollectionStateEntity"  # Default for analyze-fields

# Cleanup
ttl_field: "expireAt"
delete_missing_ttl: true
batch_size: 500

# Analysis
group_by_field: null

# Logging
log_level: "INFO"
```

## CLI usage

```bash
# Kind-level counts and size estimates
lsu analyze-kinds --project my-project

# Use all namespaces/kinds by default, or restrict explicitly
lsu analyze-kinds --namespace "" --namespace tenant-a --kind SourceCollectionStateEntity

# Field contribution analysis (falls back to config.kind/config.namespace if not provided)
lsu analyze-fields --kind SourceCollectionStateEntity --namespace "" --group-by batchId

# TTL cleanup across namespaces/kinds (dry-run)
lsu cleanup --ttl-field expireAt --dry-run

# TTL cleanup restricted to specific namespaces/kinds
lsu cleanup --namespace "" --namespace tenant-a --kind pipeline-job
```

Use `--help` on any command for full options. Config can be provided via `config.yaml` or flags.

## Development

- Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

- Install the package in editable mode with developer dependencies:

```bash
# Preferred: use the optional dev extras if your environment supports them
pip install -e .[dev]

# Or: install package then dev requirements
pip install -e .
pip install pytest google-cloud-datastore tqdm
```

- Run tests using the venv python (ensures google-cloud packages are available):

```bash
.venv/bin/python -m pytest -q
```

- Lint/format (optional if you use pre-commit/CI):

```bash
pip install ruff black
ruff check .
black .
```

## Publishing

- Automated: pushing to `main` triggers versioning, tagging, GitHub release, and PyPI publish via semantic-release.
- Prerequisites:
  - Add a PyPI token to repo secrets as `PYPI_API_TOKEN`.
  - Use conventional commits for proper versioning.

Main branch should be protected (require PRs, disallow direct pushes) in repository settings.

## Emulator & integration testing

For integration tests that exercise the Datastore emulator, there's a small helper script that
starts the emulator, waits for it to become healthy, and seeds it with deterministic test data:

```bash
# start emulator and seed using the project's .venv python (preferred)
./scripts/run_emulator_local.sh

# If you prefer to start the emulator without seeding (e.g. to seed manually),
# use the --no-seed flag:
./scripts/run_emulator_local.sh --no-seed
```

The script prefers `.venv/bin/python` if present, and falls back to `python3` or `python`.

Once the emulator is running and seeded, run the integration tests with the Makefile target:

```bash
# create a venv (see Development section), install deps, then:
make integration
```

Integration tests will skip automatically when no emulator is available, so running `make unit`
is a fast way to run only pure-unit tests.
