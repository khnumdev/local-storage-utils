#!/usr/bin/env bash
set -euo pipefail

# Simple helper to start the Datastore emulator locally and seed it with test data.
# Prefers the project's .venv python if available, otherwise falls back to python3 or python.
# Requires: gcloud SDK installed and authenticated, and python deps installed in a venv (optional).

PORT=${PORT:-8010}
PROJECT=${PROJECT:-dummy-project}

# Simple arg parsing: --no-seed to skip running the seed script, --help for usage
DO_SEED=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-seed)
      DO_SEED=0
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--no-seed]" && exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Usage: $0 [--no-seed]" >&2
      exit 2
      ;;
  esac
done

# Choose python: .venv/bin/python > python3 > python
VENV_PY=".venv/bin/python"
if [ -x "${VENV_PY}" ]; then
  PY="${VENV_PY}"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "No python executable found (python3/python) and .venv not present" >&2
  exit 1
fi

echo "Starting Datastore emulator on localhost:${PORT} (project=${PROJECT})"
gcloud beta emulators datastore start --host-port=localhost:${PORT} --project=${PROJECT} &
EM_PID=$!

echo "Waiting for emulator to accept connections on localhost:${PORT}..."
for i in {1..60}; do
  if nc -z localhost ${PORT}; then
    echo "Emulator is up"
    break
  fi
  sleep 1
done

if ! nc -z localhost ${PORT}; then
  echo "Emulator did not start in time" >&2
  kill ${EM_PID} || true
  exit 1
fi

export DATASTORE_EMULATOR_HOST=localhost:${PORT}
export DATASTORE_PROJECT_ID=${PROJECT}

if [ "${DO_SEED}" -eq 1 ]; then
  echo "Seeding emulator (running scripts/seed_emulator.py) using ${PY}"
  if "${PY}" scripts/seed_emulator.py; then
    echo "Seed succeeded"
  else
    echo "Seed failed" >&2
    kill ${EM_PID} || true
    exit 1
  fi
else
  echo "Skipping seeding (started with --no-seed)"
fi

echo "Datastore emulator started${DO_SEED:+ and seeded}. PID=${EM_PID}"
echo "To stop the emulator: kill ${EM_PID}"
