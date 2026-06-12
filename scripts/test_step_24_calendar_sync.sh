#!/usr/bin/env bash
set -euo pipefail

API=${API:-http://localhost:8000/api/v1}
EMAIL="step24-$(date +%s)@example.com"
PASSWORD="StrongPass123!"

echo "Registering test user..."
curl -sS -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Step 24 Tester\"}" >/dev/null || true

TOKEN=$(curl -sS -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

AUTH=( -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" )

echo "Checking providers..."
curl -sS "$API/calendars/providers" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "Creating demo ICS source..."
SOURCE_ID=$(curl -sS -X POST "$API/calendars/ics-sources" "${AUTH[@]}" \
  -d '{"name":"US Holidays Demo","provider":"generic_ics","ics_url":"https://www.officeholidays.com/ics/usa"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "Testing source..."
curl -sS -X POST "$API/calendars/sources/$SOURCE_ID/test" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "Syncing source..."
curl -sS -X POST "$API/calendars/sources/$SOURCE_ID/sync" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "Listing events..."
curl -sS "$API/calendars/events" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -80

echo "Step 24 calendar sync smoke test completed."
