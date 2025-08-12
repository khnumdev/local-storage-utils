# local-storage-utils

Utilities for analyzing and managing local Datastore/Firestore (Datastore mode) data. Works with both the Datastore Emulator and GCP using Application Default Credentials.

## Install (PyPI)

```bash
pip install local-storage-utils
```

This installs the `lsu` CLI.

## Install (from source)

```bash
git clone <this-repo-url>
cd local-storage-utils
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Configuration

- By default, the CLI loads `config.yaml` from the current directory if present.
- Any CLI flag overrides values from `config.yaml`.
- If neither config nor flags provide a value, the tool falls back to environment variables (for emulator detection) or sensible defaults.

Key settings in `config.yaml`:

```yaml
project_id: "my-project"          # If omitted, ADC/env will be used
emulator_host: "localhost:8010"   # If set, uses Datastore Emulator

# Explicit filters (empty means all)
namespaces: [""]                   # Empty -> iterate all namespaces (including default "")
kinds: []                          # Empty -> iterate all kinds per namespace

# Optional defaults
kind: "SourceCollectionStateEntity"  # Default for analyze-fields
namespace: ""                         # Default namespace for analyze-fields

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

- Create a virtual environment and install in editable mode as shown above
- Run tests:

```bash
python -m pip install pytest
pytest -q
```

- Lint/format (optional if you use pre-commit/CI):
```bash
python -m pip install ruff black
ruff check .
black .
```

## Publishing

- CI is configured to publish to PyPI on tags `v*`.
- Create a PyPI token and add it to repository secrets as `PYPI_API_TOKEN`.
- Tag and push:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The GitHub Actions workflow will build and upload the package to PyPI.
