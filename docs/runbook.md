# Task Tracker – Incident Runbook

Owner: Raghavapuram Sai Harshith · Service: Task Tracker (app + PostgreSQL) · Dashboard: Grafana → *Task Tracker – Service Overview* · Alerts: Prometheus → *Alerts*

## Severity levels

| Level | Meaning | Example | Response target |
|---|---|---|---|
| SEV-1 | Service unavailable for all users | `TaskTrackerDown` firing | Start within 5 min |
| SEV-2 | Service degraded (errors or slowness) | `TaskTrackerHighErrorRate`, `TaskTrackerHighLatency` | Start within 30 min |
| SEV-3 | Early warning, no user impact yet | `TaskTrackerHighCPU` | Next working hours |

## Common first steps (every incident)

1. Acknowledge the alert and note the start time.
2. Open the Grafana dashboard; check **Service status**, **Request rate by status code**, **Latency percentiles**, **CPU usage**.
3. `docker compose ps` – are all containers `Up (healthy)`?
4. `curl -s localhost:8000/health` – is the app up, and is the database `ok`?
5. `docker compose logs --since 15m app | python3 scripts/analyze_logs.py` – what changed?

---

## 1. Service down

**Alert:** `TaskTrackerDown` – `up{job="task-tracker"} == 0` for 1 minute.

**Detection:** Prometheus alert, `scripts/healthcheck.sh` prints `ALERT service DOWN`, the UI header shows *unreachable*.

**Triage**

```bash
docker compose ps                       # app Exited / Restarting / unhealthy?
docker compose logs --tail 100 app      # crash traceback, "database not ready", OOM?
docker inspect task-tracker-app-1 --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
docker compose ps db                    # is PostgreSQL healthy?
```

**Mitigation**

| Cause found | Action |
|---|---|
| Container exited or crash-looping | `docker compose up -d app`; if the newest image is at fault, roll back (below) |
| `OOMKilled: true` | raise `memory` limit in `docker-compose.yml`, `docker compose up -d app` |
| Database unhealthy | `docker compose restart db`, wait for `healthy`, then `docker compose restart app` |
| Port 8000 taken by another process | `sudo ss -ltnp 'sport = :8000'`, stop the other process |

**Roll back to the previous image**

```bash
docker pull ghcr.io/<user>/devops-task-tracker:sha-<previous>
docker tag  ghcr.io/<user>/devops-task-tracker:sha-<previous> task-tracker:local
docker compose up -d --no-build app
```

**Verify recovery:** `/health` returns 200, `up == 1` in Prometheus, alert resolves, smoke test passes: `bash scripts/smoke_test.sh`.

---

## 2. High error rate

**Alert:** `TaskTrackerHighErrorRate` – more than 5 % of requests return 5xx for 5 minutes.

**Triage**

```bash
docker compose logs --since 10m app | grep '"level": "ERROR"' | tail -20
docker compose logs --since 10m app | python3 scripts/analyze_logs.py   # which endpoint?
curl -s localhost:8000/health                                           # "database": "unavailable"?
```

**Mitigation:** database unavailable → restart `db` as in §1. Errors began right after a deployment → roll back to the previous image. One endpoint only → check its recent code change, roll back if needed.

**Verify:** the 5xx line on *Request rate by status code* drops to zero; the alert resolves.

---

## 3. High latency or high CPU

**Alerts:** `TaskTrackerHighLatency` (p95 > 500 ms for 5 min) · `TaskTrackerHighCPU` (> 0.8 core for 10 min).

**Triage**

```bash
docker stats --no-stream                       # CPU / memory per container
docker compose top app                         # gunicorn threads alive?
docker compose logs --since 10m app | python3 scripts/analyze_logs.py   # slowest endpoints
```

**Mitigation**

* Traffic spike → temporarily raise `cpus` in `docker-compose.yml`, or run more app instances behind a load balancer.
* One slow endpoint (e.g. listing many tasks) → add pagination or a database index.
* A stuck request or runaway loop → `docker compose restart app` to restore service, then investigate.
* Database slow → check `docker stats` for the `db` container and long-running queries (`pg_stat_activity`).

**Verify:** p95 back under 250 ms and CPU under 0.5 core on the dashboard for 15 minutes.

---

## Post-mortem (blameless) – template

Write within 48 hours for every SEV-1 and SEV-2.

| Section | Content |
|---|---|
| Summary | One paragraph: what happened, impact, duration |
| Timeline | Detection → acknowledgement → mitigation → recovery (with times) |
| Root cause | Technical cause and why safeguards did not prevent it |
| Detection | Which alert fired; time to detect; could it have been earlier? |
| What went well / badly | Honest list, no blame on individuals |
| Action items | Owner + due date for each fix (code, alert, runbook, test) |
