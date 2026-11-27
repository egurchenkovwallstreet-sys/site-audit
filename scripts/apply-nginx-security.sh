#!/usr/bin/env bash
# На VPS: заголовки безопасности для audit152fz.online + server_tokens off
set -euo pipefail

CONF="/etc/nginx/sites-available/site-audit-domain"
SNIP="/etc/nginx/conf.d/site-audit-security-headers.conf"

if [[ ! -f "$CONF" ]]; then
  echo "Нет $CONF — сначала подключите домен (docs/domain-reg-ru.md)."
  exit 1
fi

cat > "$SNIP" <<'EOF'
# Подключается в server { } audit152fz.online (listen 443)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Resource-Policy "same-site" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'" always;
EOF

if ! grep -q "site-audit-security-headers" "$CONF"; then
  sed -i '/listen 443 ssl;/a \    include /etc/nginx/conf.d/site-audit-security-headers.conf;' "$CONF"
fi

if ! grep -q 'server_tokens off' /etc/nginx/nginx.conf; then
  sed -i '/http {/a \    server_tokens off;' /etc/nginx/nginx.conf
fi

for block in location; do
  if ! grep -q 'proxy_hide_header X-Powered-By' "$CONF"; then
    sed -i '/proxy_pass http:\/\/site_audit_front_domain;/a \        proxy_hide_header X-Powered-By;' "$CONF"
    break
  fi
done

nginx -t
systemctl reload nginx
echo "OK: security headers + server_tokens applied"