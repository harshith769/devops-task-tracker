# DevOps Task Tracker

![CI/CD](https://github.com/harshith769/devops-task-tracker/actions/workflows/ci-cd.yml/badge.svg)

End-to-end DevOps pipeline for a small web application, built during the **DevOps internship at Alfido Tech** (21 Sep – 21 Oct 2026) by **Raghavapuram Sai Harshith**.

| Task | What is in this repo |
|---|---|
| Beginner tasks | Linux command notes (`docs/linux-basics.md`), backup and log-rotation scripts (`scripts/`) |
| 1 – Containerization | Multi-stage `Dockerfile`, `docker-compose.yml` (app + PostgreSQL + Prometheus + Grafana) |
| 2 – CI/CD | `.github/workflows/ci-cd.yml`: lint → test → Terraform validate → build & push to GHCR → deploy to staging → smoke test |
| 3 – Infrastructure as Code | `terraform/`: VPC, subnet, internet gateway, route table, security group, EC2 VM, versioned S3 bucket on a local AWS emulator |
| 4 – Monitoring & incident response | `/metrics` endpoint, Prometheus scrape config and alert rules, Grafana dashboard, JSON logs, `docs/runbook.md` |

## The application

A Flask REST API with a small web UI for managing tasks, backed by PostgreSQL (SQLite when run without a database).

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Web UI |
| GET | `/health` | Liveness + database check (200 / 503) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/tasks[?status=todo\|in_progress\|done]` | List tasks |
| POST | `/api/tasks` | Create `{"title": "...", "priority": "low\|medium\|high"}` |
| GET / PATCH / DELETE | `/api/tasks/<id>` | Read / update / delete one task |

## Requirements

* Docker Desktop (Windows/macOS) or Docker Engine + Compose plugin (Linux)
* Git, Python 3.12+ (for tests and scripts), Terraform 1.5+ (Task 3)

## Task 1 – Run with Docker

```bash
cp .env.example .env                 # optional: change passwords
docker compose up -d --build         # build the image and start all 4 services
docker compose ps                    # app and db should show (healthy)
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" \
     -d '{"title": "Dockerize the app", "priority": "high"}'
curl http://localhost:8000/api/tasks
```

| Service | URL |
|---|---|
| Task Tracker | http://localhost:8000 |
| Prometheus | http://localhost:9090 (Status → Targets, Alerts) |
| Grafana | http://localhost:3000 (admin / admin) → Dashboards → Task Tracker |

Build and run the image alone (uses SQLite inside the container):

```bash
docker build -t task-tracker:local .
docker run -d --name tt -p 8000:8000 task-tracker:local
docker images task-tracker            # image size
docker rm -f tt
```

Stop everything: `docker compose down` (add `-v` to delete the data volumes).

## Task 2 – CI/CD with GitHub Actions

Every push to `main` runs `.github/workflows/ci-cd.yml`:

1. **Lint & test** – flake8, pytest with coverage (reports uploaded as artifacts)
2. **Terraform validate** – `terraform init -backend=false` + `terraform validate`
3. **Build & push image** – Docker Buildx, tags `sha-<commit>` and `latest`, pushed to GitHub Container Registry (`ghcr.io`) using the built-in `GITHUB_TOKEN` (no secrets to configure)
4. **Deploy to staging & smoke test** – pulls the new image, runs it against a PostgreSQL service container and runs `scripts/smoke_test.sh`

Pull requests run steps 1–3 without pushing. The run history is under the **Actions** tab, and the image under **Packages** on your profile.

## Task 3 – Terraform

Terraform talks to a local AWS emulator on port 4566, so no AWS account or cost is involved. [Moto server](https://github.com/getmoto/moto) is used because it is free and needs no account (LocalStack works too, but since March 2026 it needs a LocalStack auth token).

```bash
pip install "moto[server]"
moto_server -p 4566                  # leave running in a separate terminal

cd terraform
terraform init                       # download the AWS provider
terraform fmt -check
terraform validate
terraform plan -out tfplan           # preview: 10 resources to add
terraform apply tfplan
terraform output
terraform state list
terraform destroy                    # clean up
```

State is stored locally in `terraform.tfstate` (git-ignored). `backend.tf.example` shows how to move it to a versioned S3 bucket with locking for team use.

## Task 4 – Monitoring, logging and incident response

* Metrics: `http_requests_total`, `http_request_duration_seconds` (histogram), `http_requests_in_progress`, `tasks_current`, `tasks_created_total`, process CPU/memory.
* Alerts (`monitoring/prometheus/alert_rules.yml`): service down, 5xx error rate > 5 %, p95 latency > 500 ms, CPU > 80 %.
* Logs: one JSON object per line on stdout, collected by Docker's `json-file` driver with rotation (10 MB × 3 files).

```bash
python3 scripts/load_test.py --duration 60 --concurrency 8     # generate traffic
docker compose logs app --no-log-prefix | python3 scripts/analyze_logs.py
./scripts/healthcheck.sh http://localhost:8000/health 5        # watch for outages
docker compose stop app      # incident drill: TaskTrackerDown fires after 1 min
docker compose start app     # recovery
```

Runbook: [`docs/runbook.md`](docs/runbook.md).

## Run the tests locally

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
flake8 app tests wsgi.py scripts
pytest -v --cov=app
```

Static checks of every config file (Dockerfile, workflow, scripts, Compose, PromQL, Terraform, YAML):

```bash
pip install hadolint-py actionlint-py shellcheck-py promql-parser python-hcl2 pyyaml
bash scripts/check_configs.sh
```

## Repository layout

```
app/                     Flask application (routes, models, metrics, JSON logging, UI)
tests/                   pytest unit tests
scripts/                 backup, log rotation, health check, log analysis, load test, smoke test, config checks
Dockerfile               multi-stage image build
docker-compose.yml       app + PostgreSQL + Prometheus + Grafana
.github/workflows/       CI/CD pipeline
terraform/               infrastructure as code
monitoring/              Prometheus config + alert rules, Grafana provisioning + dashboard
docs/                    incident runbook, Linux notes
```
