#!/usr/bin/env bash
set -euo pipefail
cd /root/apps/site-audit
git pull
if [ ! -f .env ]; then
  PASS=$(openssl rand -hex 16)
  cat > .env <<EOF
APP_ENV=production
SITE_ADDRESS=:80
NEXT_PUBLIC_API_URL=http://194.87.220.206:8080
CORS_ORIGINS=http://194.87.220.206:8080
POSTGRES_DB=site_audit
POSTGRES_USER=site_audit
POSTGRES_PASSWORD=${PASS}
DATABASE_URL=postgresql+asyncpg://site_audit:${PASS}@db:5432/site_audit
GIGACHAT_AUTH_KEY=
YOOKASSA_SHOP_ID=
PAYMENT_RETURN_URL=http://194.87.220.206:8080/reports
EOF
fi
cp deploy/nginx-site-audit.conf /etc/nginx/sites-available/site-audit
ln -sf /etc/nginx/sites-available/site-audit /etc/nginx/sites-enabled/site-audit
nginx -t
systemctl reload nginx
docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml up -d --build db backend frontend
docker compose -f docker-compose.yml -f deploy/docker-compose.witty.yml ps