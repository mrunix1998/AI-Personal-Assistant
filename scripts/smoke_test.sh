#!/usr/bin/env bash
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
EMAIL=${EMAIL:-saba@test.com}
PASSWORD=${PASSWORD:-StrongPass123}

echo "Health..."
curl -s "$BASE/api/v1/health" | jq .

echo "Register..."
curl -s -X POST "$BASE/api/v1/auth/register" -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Saba Test\"}" | jq . || true

echo "Login..."
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r .access_token)
echo "TOKEN=$TOKEN"

echo "Create task..."
curl -s -X POST "$BASE/api/v1/tasks" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"title":"Prepare CV","due_at":"2026-06-06T15:00:00Z"}' | jq .

echo "Unified agenda..."
curl -s "$BASE/api/v1/agenda/unified-daily?agenda_date=2026-06-06" -H "Authorization: Bearer $TOKEN" | jq .

echo "Notification center daily agenda..."
curl -s -X POST "$BASE/api/v1/notifications/center/daily-agenda?agenda_date=2026-06-06" -H "Authorization: Bearer $TOKEN" | jq .

echo "List notifications..."
curl -s "$BASE/api/v1/notifications/center" -H "Authorization: Bearer $TOKEN" | jq .

echo "Web push fake subscription..."
curl -s -X POST "$BASE/api/v1/notifications/web-push/subscriptions" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"endpoint":"https://example.com/fake-push-endpoint","p256dh":"fake-p256dh-key","auth":"fake-auth-key"}' | jq .
