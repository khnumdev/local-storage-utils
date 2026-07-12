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

## Installing from TestPyPI (for dry-runs)

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

```bash
git clone https://github.com/khnumdev/local-storage-utils.git
cd local-storage-utils
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

### Troubleshooting local installs

- If you see "Command 'python' not found", use `python3 -m venv .venv` (above). Inside the venv, `python` will point to Python 3.
- If you see "externally-managed-environment", you are attempting a system-wide install. Always install into a virtual environment:
  - Create a venv: `python3 -m venv .venv && source .venv/bin/activate`
  - Then use the venv pip: `python -m pip install -U pip && pip install -e .`

#### Installing Python 3 (if not already installed)

**macOS:**
```bash
# Install Python 3 using Homebrew
brew install python@3.12
```

**Linux (Debian/Ubuntu):**
```bash
# Install Python 3 and venv support
sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
```

**Linux (Fedora/RHEL):**
```bash
# Install Python 3 and venv support
sudo dnf install python3 python3-pip
```

**Linux (using Homebrew):**
```bash
# Install Homebrew first (if not already installed): https://brew.sh
# Then install Python 3
brew install python@3.12
```

## Configuration

Create an optional `config.yaml` in your working directory to customize behavior. **By default, all commands iterate over all namespaces and all kinds** unless you specify filters.

### Minimal Example

```yaml
# Optional: specify project and emulator
project_id: "my-project"
emulator_host: "localhost:8010"
```

### Common Options

```yaml
# Optional filters (omit to process all namespaces and kinds)
namespaces: ["custom-ns"]  # List specific namespaces, or omit to process all
kinds: ["MyKind"]          # List specific kinds, or omit to process all

# Cleanup settings
ttl_field: "expireAt"      # Field name containing expiry timestamp
batch_size: 500            # Delete batch size

# Analysis settings
sample_size: 500           # Max entities to sample per analysis (0 = no limit)
```

**Notes:**
- CLI flags always override config values
- If no config is provided, sensible defaults are used
- Environment variables `DATASTORE_PROJECT_ID` and `DATASTORE_EMULATOR_HOST` are also supported

## Quickstart

Lightweight utilities for analyzing and cleaning Datastore (Firestore in Datastore mode). Works with the Datastore emulator for local integration testing or GCP when using Application Default Credentials.

### Quick overview

- CLI: run commands via `python3 cli.py <command>` (or install the package and use the entrypoint).
- Makefile: convenience targets are provided to create a venv, install deps, and run tests locally.

### Quickstart (from source)
```bash
git clone https://github.com/khnumdev/local-storage-utils.git
cd local-storage-utils
# create a venv and install the package in editable mode
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### Makefile shortcuts

- `make venv` — create `.venv` and install package in editable mode
- `make unit` — run fast unit tests
- `make integration` — run integration tests (starts/seeds emulator when configured)

Use these targets to get a working dev environment quickly.

### Basic CLI examples
```bash
# Analyze all kinds in all namespaces (default behavior)
lsu analyze-kinds

# Analyze specific kind across all namespaces
lsu analyze-fields --kind MyKind

# Analyze with grouping
lsu analyze-fields --kind MyKind --group-by batchId

# Dry-run cleanup for all kinds and namespaces
lsu cleanup --dry-run

# Filter to specific namespace and kind
lsu cleanup --kind MyKind --namespace custom-ns --dry-run
```

### Emulator & integration testing

- Start & seed emulator locally:
  - `./scripts/run_emulator_local.sh` (prefers `.venv/bin/python` to run seeder)
  - `./scripts/run_emulator_local.sh --no-seed` to skip seeding
- The seeder accepts `SEED_COUNT` and `SEED_NS_COUNT` env vars to increase dataset size for perf tests.

Run integration tests:

```bash
# create venv and install deps (see Quickstart), then:
make integration
```

### Development & tests

- Run unit tests:
  - `make unit` (fast)
- Run full test suite locally:
  - `make integration`

## Publishing

This project uses the `release` workflow to publish releases to PyPI. Follow the packaging tutorial for a complete guide on packaging and publishing: https://packaging.python.org/en/latest/tutorials/packaging-projects/

We support publishing to either TestPyPI (for dry runs) or the real PyPI. The workflow can be triggered automatically on pushes to `main` or manually via the Actions UI (use the "Run workflow" button). When you run it manually you can set the `publish_target` input to `testpypi` to publish to TestPyPI instead of PyPI.

### Secrets and tokens
- For production publishing to the real PyPI, set the repository secret named `PYPI_API_TOKEN` with a PyPI API token.
- For test publishing to TestPyPI, set the repository secret named `TEST_PYPI_API_TOKEN` with a TestPyPI API token.

The release workflow selects the appropriate token based on the `publish_target` input. Use TestPyPI first to validate packaging and metadata before publishing to the real index.

## Notes

- **By default, all commands iterate over all namespaces and all kinds** unless you specify filters via config or CLI flags
- `sample_size` bounds per-kind analysis to avoid scanning entire large datasets (set to 0 to disable)
- Multi-threaded processing is enabled by default for better performance
