#!/usr/bin/env bash
# check_configs.sh - static checks for every configuration file in the repo.
#
# One-time setup: pip install hadolint-py actionlint-py shellcheck-py promql-parser python-hcl2 pyyaml
# Usage:          bash scripts/check_configs.sh

set -uo pipefail
fail=0
step() { printf '\n== %s\n' "$*"; }
ok()   { echo "   OK"; }
bad()  { echo "   FAILED"; fail=1; }
check() { if "$@"; then ok; else bad; fi; }

step "Dockerfile (hadolint)"
check hadolint Dockerfile

step "GitHub Actions workflow (actionlint + shellcheck)"
check actionlint .github/workflows/ci-cd.yml

step "Shell scripts (shellcheck)"
check shellcheck scripts/*.sh

step "docker-compose.yml (docker compose config)"
if command -v docker > /dev/null; then
  if docker compose config --quiet; then
    echo "   services: $(docker compose config --services | xargs)"
    ok
  else
    bad
  fi
else
  echo "   docker not installed - skipped"
fi

step "Prometheus rules and Grafana dashboard queries (PromQL parser)"
if python3 - <<'EOF'
import json, yaml, promql_parser
rules = yaml.safe_load(open("monitoring/prometheus/alert_rules.yml"))
exprs = [(r["alert"], r["expr"]) for g in rules["groups"] for r in g["rules"]]
dash = json.load(open("monitoring/grafana/dashboards/task-tracker-overview.json"))
exprs += [(p["title"], t["expr"]) for p in dash["panels"] for t in p["targets"]]
for _, e in exprs:
    promql_parser.parse(e)
print(f"   {len(exprs)} PromQL expressions parsed ({len(rules['groups'][0]['rules'])} alert rules)")
EOF
then ok; else bad; fi

step "Terraform files (HCL parser)"
if python3 - <<'EOF'
import glob, hcl2
resources = []
for f in sorted(glob.glob("terraform/*.tf")):
    for block in hcl2.load(open(f)).get("resource", []):
        for rtype, body in block.items():
            resources += [f"{rtype}.{name}".replace('"', "") for name in body]
print(f"   {len(resources)} resources: " + ", ".join(resources))
EOF
then ok; else bad; fi

step "YAML syntax"
if python3 - <<'EOF'
import glob, yaml
files = glob.glob("monitoring/**/*.yml", recursive=True) + [".github/workflows/ci-cd.yml", "docker-compose.yml"]
for f in files:
    yaml.safe_load(open(f))
print(f"   {len(files)} YAML files parsed")
EOF
then ok; else bad; fi

echo
if [[ $fail -eq 0 ]]; then echo "All checks passed."; else echo "Some checks FAILED."; fi
exit $fail
