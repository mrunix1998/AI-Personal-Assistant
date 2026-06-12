#!/usr/bin/env bash
set -euo pipefail
API=${API:-http://localhost:8000}
curl -fsS "$API/openapi.json" | python -m json.tool | grep '"/api/v1/' | sort || true
