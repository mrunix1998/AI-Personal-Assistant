#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://localhost:3000 >/dev/null
curl -fsS http://localhost:8000/api/v1/health >/dev/null
curl -fsS http://localhost:8000/openapi.json | grep -q '/api/v1/integration-actions/telegram/test'
echo "Frontend + integration action endpoints are available."
