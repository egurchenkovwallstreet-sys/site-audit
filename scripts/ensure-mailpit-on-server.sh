#!/usr/bin/env bash
# На VPS: дописать Mailpit в .env, обновить nginx для :8081
set -euo pipefail
cd /root/apps/site-audit
ENV_FILE=.env

ensure_kv() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    return 0
  fi
  echo "${key}=${val}" >> "$ENV_FILE"
}

ensure_kv SMTP_HOST mailpit
ensure_kv SMTP_PORT 1025
ensure_kv SMTP_USE_SSL false
ensure_kv SMTP_STARTTLS false
ensure_kv SMTP_ALLOW_UNAUTHENTICATED true
ensure_kv SMTP_FROM site-audit@test.local
ensure_kv MAILPIT_PUBLIC_URL http://194.87.220.206:8081

if [[ -f /etc/nginx/sites-available/site-audit ]]; then
  cp deploy/nginx-site-audit.conf /etc/nginx/sites-available/site-audit
  nginx -t
  systemctl reload nginx
fi