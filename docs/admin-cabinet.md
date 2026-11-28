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
- `GET /api/admin/stats?period=day|week|month|all`
- `GET /api/admin/stats/all-periods`

## Безопасность

- Пароль **никогда** не коммитить.
- После утечки пароля в переписке — **сменить** `ADMIN_PASSWORD` на сервере.