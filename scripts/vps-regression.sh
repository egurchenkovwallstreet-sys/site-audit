#!/usr/bin/env bash
# Прогон регрессии внутри backend-контейнера (Playwright + сеть как у прод-скана).
set -euo pipefail
REPO="${REPO:-/root/apps/site-audit}"
cd "$REPO"
COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml)
"${COMPOSE[@]}" run --rm \
  -v "$REPO:/workspace:ro" \
  --no-deps \
  --entrypoint python \
  backend \
  /workspace/scripts/regression_scan.py "$@"