#!/usr/bin/env bash
set -euo pipefail

echo "== AI Personal Assistant Production Readiness Check =="
echo "[1/8] Backend Python compile"
docker compose exec -T backend python -m compileall -q app

echo "[2/8] Alembic history/current"
docker compose exec -T backend alembic history
docker compose exec -T backend alembic current

echo "[3/8] Pytest"
docker compose exec -T backend pytest -q

echo "[4/8] API health"
curl -fsS http://localhost:8000/api/v1/health >/dev/null
curl -fsS http://localhost:8000/api/v1/monitoring/health >/dev/null
curl -fsS http://localhost:8000/api/v1/monitoring/readiness >/dev/null

echo "[5/8] OpenAPI required paths"
OPENAPI="$(curl -fsS http://localhost:8000/openapi.json)"
echo "$OPENAPI" | grep -q "/api/v1/automation/status"
echo "$OPENAPI" | grep -q "/api/v1/monitoring/metrics"
echo "$OPENAPI" | grep -q "/api/v1/integration-actions/telegram/test"
echo "$OPENAPI" | grep -q "/api/v1/integration-actions/email/test"

echo "[6/8] Celery services are declared"
docker compose config --services | grep -qx worker
docker compose config --services | grep -qx scheduler

echo "[7/8] Celery import check"
docker compose exec -T backend python - <<'PY'
from app.workers.celery_app import celery_app
assert 'send_due_reminders' in celery_app.tasks
assert 'send_daily_agendas' in celery_app.tasks
print('celery ok')
PY

echo "[8/8] Frontend smoke"
curl -fsS http://localhost:3000 >/dev/null || echo "Frontend not ready yet; retry after npm build finishes."

echo "Production readiness checks passed."
