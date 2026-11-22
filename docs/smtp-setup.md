# Почта: тест без ящика (Mailpit) и боевая отправка

## 1. Тест без SMTP и без пароля (сейчас на проде)

На VPS поднят **Mailpit** — письма **не уходят в интернет**, а попадают в тестовый ящик.

1. После скана нажмите **«Текст письма»** — увидите тему и тело без отправки.
2. **«Отправить письмо»** — копия в Mailpit (получатель как на сайте, но доставка только «внутри» сервера).
3. Откройте тестовый ящик: **http://194.87.220.206:8081**

Переменные в `.env` на сервере (уже можно так настроить):

```env
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USE_SSL=false
SMTP_STARTTLS=false
SMTP_ALLOW_UNAUTHENTICATED=true
SMTP_FROM=site-audit@test.local
MAILPIT_PUBLIC_URL=http://194.87.220.206:8081
PUBLIC_SITE_URL=http://194.87.220.206:8080
```

После правки: `bash scripts/remote-redeploy.sh`.

Nginx для порта **8081**: файл `deploy/nginx-site-audit.conf` (блок Mailpit). На сервере:

```bash
cp /root/apps/site-audit/deploy/nginx-site-audit.conf /etc/nginx/sites-available/site-audit
nginx -t && systemctl reload nginx
```

## 2. Реальная доставка (когда будет ящик)

Яндекс / свой SMTP:

```env
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_STARTTLS=false
SMTP_ALLOW_UNAUTHENTICATED=false
SMTP_USER=ваш_ящик@yandex.ru
SMTP_PASSWORD=пароль_приложения
SMTP_FROM=ваш_ящик@yandex.ru
```

Mailpit можно оставить для тестов; для боя достаточно сменить `SMTP_*` и выключить `SMTP_ALLOW_UNAUTHENTICATED`.

## API

- `GET /api/scans/{id}/outreach-email-preview?to_email=...` — только текст.
- `POST /api/scans/{id}/send-preview-email` — отправка (Mailpit или SMTP).