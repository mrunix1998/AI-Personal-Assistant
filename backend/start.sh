#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for PostgreSQL..."
until pg_isready -h db -p 5432 -U postgres >/dev/null 2>&1; do
  sleep 2
done

echo "PostgreSQL is ready"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
fi

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_EXTRA_ARGS:-}
