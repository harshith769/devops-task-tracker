#!/usr/bin/env bash
# healthcheck.sh - poll the /health endpoint, report UP/DOWN transitions and
#                  measure how long an outage lasted.
#
# Usage: ./scripts/healthcheck.sh [url] [interval_seconds] [checks]
#        checks = 0 means run forever (e.g. inside tmux or as a systemd service)
# Exit:  0 if the last check was healthy, 1 otherwise (useful in cron / CI).

URL="${1:-http://localhost:8000/health}"
INTERVAL="${2:-5}"
CHECKS="${3:-0}"

state="UNKNOWN"
down_since=0
n=0

ts() { date '+%Y-%m-%d %H:%M:%S'; }

while :; do
  n=$((n + 1))
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$URL")
  if [[ "$code" == "200" ]]; then
    if [[ "$state" == "DOWN" ]]; then
      echo "$(ts) RECOVERED  service healthy again after $(( $(date +%s) - down_since ))s"
    fi
    state="UP"
    echo "$(ts) UP         HTTP $code  $URL"
  else
    if [[ "$state" != "DOWN" ]]; then
      down_since=$(date +%s)
      echo "$(ts) ALERT      service DOWN (HTTP ${code:-000}) - follow docs/runbook.md#1-service-down"
    fi
    state="DOWN"
    echo "$(ts) DOWN       HTTP ${code:-000}  $URL"
  fi
  if [[ "$CHECKS" -gt 0 && "$n" -ge "$CHECKS" ]]; then break; fi
  sleep "$INTERVAL"
done

[[ "$state" == "UP" ]]
