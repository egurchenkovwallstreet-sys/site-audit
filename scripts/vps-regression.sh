#!/usr/bin/env bash
# Прогон регрессии через работающий backend-контейнер (Playwright уже есть).
set -euo pipefail
REPO="${REPO:-/root/apps/site-audit}"
cd "$REPO"
COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml)
CID="$("${COMPOSE[@]}" ps -q backend)"
if [[ -z "$CID" ]]; then
  echo "backend container not running" >&2
  exit 1
fi
docker cp "$REPO/scripts/regression_scan.py" "$CID:/tmp/regression_scan.py"
docker cp "$REPO/scripts/regression_urls.json" "$CID:/tmp/regression_urls.json"
"${COMPOSE[@]}" exec -T backend \
  python /tmp/regression_scan.py --file /tmp/regression_urls.json "$@"