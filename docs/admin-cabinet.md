# Админ-кабинет (статистика)

**URL:** `https://audit152fz.online/admin/login` → `/admin/dashboard`

**Доступ:** только переменные в **`.env` на VPS** (не в git):

```env
ADMIN_EMAIL=ваш@email.ru
ADMIN_PASSWORD=длинный_секретный_пароль
ADMIN_SESSION_SECRET=случайная_строка_32+_байт
```

Сгенерировать секрет сессии:

```bash
openssl rand -hex 32
```

После изменения `.env` — перезапуск backend (`remote-redeploy.sh` не перезаписывает `.env`).

## API

- `POST /api/admin/login` — cookie `site_audit_admin`
- `GET /api/admin/stats?period=day|week|month|all` — в т.ч. **новые IP**, **оплаты отчётов** (таблица `payments`, статус `succeeded`)
- `GET /api/admin/stats/all-periods`
- `GET /api/admin/incidents` — сбои проверок (обновление в UI ~30 с)
- `POST /api/admin/incidents/{id}/resolve`

## Проверки: 10 + 10 минут

Первая фаза — `SCAN_TIME_BUDGET_SEC` (по умолчанию 600 с). При таймауте — автоматически
`+SCAN_TIME_EXTENSION_SEC` (ещё 600 с). После 20 минут — диагностика в инциденте; при наличии
данных клиенту отдаётся **частичный** результат. Сбои «на нашей стороне» — автоповтор до
`SCAN_AUTO_RETRY_MAX`.

## Безопасность

- Пароль **никогда** не коммитить.
- После утечки пароля в переписке — **сменить** `ADMIN_PASSWORD` на сервере.