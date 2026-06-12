#!/usr/bin/env bash
set -euo pipefail

echo "Checking frontend root..."
curl -fsS http://localhost:3000 >/dev/null
echo "Frontend OK"

echo "Checking backend health..."
curl -fsS http://localhost:8000/api/v1/health
echo

echo "Checking calendar providers..."
curl -fsS http://localhost:8000/api/v1/calendar/providers | jq .
