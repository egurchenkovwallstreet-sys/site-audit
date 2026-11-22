# SMTP для тестовой отправки с экрана скана

Кнопка **«Отправить письмо»** вызывает `POST /api/scans/{id}/send-preview-email` и шлёт текст по шаблону **`docs/outreach-machine-tz.md` §5.4** на адрес из найденных на сайте.

## Переменные в `.env` (на сервере)

```env
PUBLIC_SITE_URL=http://194.87.220.206:8080

SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_STARTTLS=false
SMTP_USER=ваш_ящик@yandex.ru
SMTP_PASSWORD=пароль_приложения
SMTP_FROM=ваш_ящик@yandex.ru
```

После правки `.env`: `bash scripts/remote-redeploy.sh` (пересоздаёт backend с новым env).

Пароль — **пароль приложения** почты, не основной пароль аккаунта.

## Ограничения

- Только на адреса из `context.contact_emails` этого скана.
- Не чаще 1 раза в 90 секунд на один `scan_id`.
- Без SMTP — ответ **503** с подсказкой.