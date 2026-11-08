#!/usr/bin/env bash
# smoke_test.sh - post-deployment check used by the CI/CD pipeline.
# Waits for /health, then exercises the API end to end.
#
# Usage: bash scripts/smoke_test.sh [base_url] [timeout_seconds]

set -euo pipefail
BASE="${1:-http://localhost:8000}"
TIMEOUT="${2:-60}"

echo "Waiting up to ${TIMEOUT}s for $BASE/health ..."
for ((i = 1; i <= TIMEOUT; i++)); do
  if curl -fsS "$BASE/health" > /dev/null 2>&1; then
    echo "  healthy after ${i}s: $(curl -fsS "$BASE/health")"
    break
  fi
  if [[ "$i" -eq "$TIMEOUT" ]]; then
    echo "  service did not become healthy in ${TIMEOUT}s" >&2
    exit 1
  fi
  sleep 1
done

echo "Creating a task ..."
created=$(curl -fsS -X POST "$BASE/api/tasks" -H 'Content-Type: application/json' \
  -d '{"title": "smoke test", "priority": "low"}')
echo "  $created"
id=$(echo "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

echo "Reading task $id back ..."
curl -fsS "$BASE/api/tasks/$id" > /dev/null

echo "Checking validation returns HTTP 400 ..."
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/tasks" \
  -H 'Content-Type: application/json' -d '{"title": ""}')
[[ "$code" == "400" ]] || { echo "  expected 400, got $code" >&2; exit 1; }

echo "Checking /metrics is exposed ..."
metrics=$(curl -fsS "$BASE/metrics")
grep -q '^http_requests_total' <<< "$metrics" || { echo "  /metrics missing counters" >&2; exit 1; }

echo "Smoke test passed."
