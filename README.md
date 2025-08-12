# local-storage-utils

Utilities for analyzing and managing local Datastore/Firestore (Datastore mode) data. Works with both the Datastore Emulator and GCP using Application Default Credentials.

## Install

```bash
pip install -e .
```

## CLI

```bash
# Kind-level counts and size estimates
lsu analyze-kinds --project my-project

# Field contribution analysis for a kind
lsu analyze-fields --kind SourceCollectionStateEntity --namespace "" --group-by batchId

# TTL cleanup across kinds/namespaces (dry-run)
lsu cleanup --ttl-field expireAt --dry-run
```

Use `--help` on any command for full options. Config can be provided via `config.yaml` or flags.
