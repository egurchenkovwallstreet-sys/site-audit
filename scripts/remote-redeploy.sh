#!/usr/bin/env bash
# Только на сервере: pull + rebuild без пересоздания .env
set -euo pipefail
cd /root/apps/site-audit
git pull
bash scripts/ensure-mailpit-on-server.sh
docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml up -d --build db mailpit backend frontend
docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml ps