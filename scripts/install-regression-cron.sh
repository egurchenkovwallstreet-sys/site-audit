#!/usr/bin/env bash
# Установка crontab для плановой регрессии (только на VPS, от root).
set -euo pipefail

REPO="${REPO:-/root/apps/site-audit}"
CRON_MARKER="# site-audit-regression"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запускайте от root на сервере." >&2
  exit 1
fi

chmod +x "$REPO/scripts/scheduled-regression.sh"
chmod +x "$REPO/scripts/vps-regression.sh"
mkdir -p /var/log/site-audit

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | grep -v "scheduled-regression.sh" >"$TMP" || true

cat >>"$TMP" <<EOF
$CRON_MARKER
CRON_TZ=Europe/Moscow
# Каждое воскресенье 01:30 — строгие 9 URL (~20 мин)
30 1 * * 0 $REPO/scripts/scheduled-regression.sh weekly
# 1-е число месяца 01:15 — панель 50 (~2–4 ч; низкий приоритет CPU/IO)
15 1 1 * * $REPO/scripts/scheduled-regression.sh monthly
EOF

crontab "$TMP"
rm -f "$TMP"

echo "Crontab установлен:"
crontab -l | grep -A3 "$CRON_MARKER" || true
echo "Логи: /var/log/site-audit/regression.log"