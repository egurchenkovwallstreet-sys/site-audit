# Снимок продакшена site-audit

**Назначение:** зафиксировать, что реально работает на VPS, без секретов.  
**Обновлять:** после деплоя, который меняет инфраструктуру, `.env` или продуктовые лимиты.  
**В PROGRESS:** краткая версия и дата — см. раздел «Снимок продакшена» в `PROGRESS.md`.

Последняя проверка: **2026-11-27** (ориентир commit `6d3bf54`; **фаза A закрыта**, далее фаза B — `docs/launch-phase-b-tz.md`).

## Доступ и пути

| Параметр | Значение |
|----------|----------|
| UI + API | http://194.87.220.206:8080 |
| Mailpit (просмотр писем) | http://194.87.220.206:8081 |
| VPS | `root@194.87.220.206` |
| Каталог | `/root/apps/site-audit` |
| Репозиторий | https://github.com/egurchenkovwallstreet-sys/site-audit (`main`) |
| Деплой | `ssh root@194.87.220.206 "bash /root/apps/site-audit/scripts/remote-redeploy.sh"` |

Порт **:80** на хосте занят другим проектом (**ai-aggregator**); site-audit отдаётся через **nginx на :8080 и :8081**.

## Прокси (факт на хосте)

- **nginx** (`deploy/nginx-site-audit.conf` → `/etc/nginx/sites-enabled/site-audit`)
  - `:8080` → frontend `127.0.0.1:3001`, `/api/` → backend `127.0.0.1:8001`
  - `:8081` → Mailpit UI `127.0.0.1:8025`
- Сервис **caddy** из `docker-compose.yml` на проде **не запущен** (только db, backend, frontend, mailpit).

## Docker Compose (работающие сервисы)

| Сервис | Образ | Порты на хосте |
|--------|-------|----------------|
| `db` | `postgres:16-alpine` | внутренняя сеть |
| `backend` | сборка `backend/` (Playwright Python + Nuclei в образе) | `127.0.0.1:8001→8000` |
| `frontend` | сборка `frontend/` (Next.js) | `127.0.0.1:3001→3000` |
| `mailpit` | `axllent/mailpit:v1.21` | `127.0.0.1:8025` (SMTP 1025 внутри сети) |

## Переменные `.env` на сервере (без секретов)

Задано **явно** (остальное — дефолты из `backend/app/config.py` внутри образа):

- `APP_ENV=production`
- `SITE_ADDRESS=:80` (для Caddy, если включат; сейчас не используется)
- `PUBLIC_SITE_URL=http://194.87.220.206:8080`
- `NEXT_PUBLIC_API_URL=http://194.87.220.206:8080`
- `CORS_ORIGINS=http://194.87.220.206:8080`
- `PAYMENT_RETURN_URL=http://194.87.220.206:8080/reports`
- Postgres: `POSTGRES_*`, `DATABASE_URL` (пароль только на сервере)
- SMTP тест: `SMTP_HOST=mailpit`, порт `1025`, `SMTP_ALLOW_UNAUTHENTICATED=true`, `MAILPIT_PUBLIC_URL=http://194.87.220.206:8081`
- `GIGACHAT_*`, `YOOKASSA_*` — **не настроены** (фаза B)

**Нет в `.env`** (и это нормально): `SCAN_MAX_PAGES`, `SCAN_TIME_BUDGET_SEC`, `PLAYWRIGHT_*`, `NUCLEI_*`, `PASSIVE_PROBE_MAX` — берутся из кода образа.

## Эффективные настройки скана (проверено в контейнере backend)

| Параметр | Значение |
|----------|----------|
| `scan_max_pages` | **30** |
| `scan_time_budget_sec` | **600** (10 мин) |
| `playwright_enabled` | true |
| `playwright_max_fetches` | **14** |
| `nuclei_enabled` | true |
| `nuclei_timeout_sec` | **120** |
| `passive_probe_max` | **12** |

Источник: `get_settings()` в running backend после деплоя `f704f15`.

## Продуктовое поведение на проде (фаза A — завершена)

- На странице `/check/{id}` показываются **все** findings (без paywall по тарифу).
- UI-таймер **10:00**; при раннем `completed` — ускорение **циферблата** (+20% к скорости каждую секунду), моргание **контура** блока (цифры статичны), затем результат.
- Если таймер истёк, а скан ещё `running` — доп. ожидание и до **2** автоперезапусков (`POST /api/scans/{id}/restart`), stale → `failed`.
- Блок **«Итого»**: каждое compliance-нарушение в тексте как **критическое** («найдено N критических нарушений… уже сейчас ведут к штрафам»); у security — «всего N уязвимостей, из них M критических» + строка повторного нарушения.
- Отчёты **HTML** short/extended: API `paid-report` / `download` (оплата ЮKassa **не** подключена).
- Антибот/честный scope: `docs/report-policy.md`, `.cursor/rules/report-antibot-policy.mdc`.

## Регрессия (cron, MSK)

```
30 1 * * 0  .../scheduled-regression.sh weekly   # 9 strict URL
15 1 1 * *  .../scheduled-regression.sh monthly  # панель 50
```

См. `docs/regression-panel.md`, `scripts/regression_urls.json`.

## Следующий этап (фаза B)

1. Домен + HTTPS и обновление `PUBLIC_SITE_URL` / CORS.
2. Безопасность API (rate limit, SSRF).
3. ЮKassa и гейт скачивания отчётов.

Подробно: **`docs/launch-phase-b-tz.md`**.

## Что не на проде / отложено

- ЮKassa, гейт платных отчётов, GigaChat.
- ZAP как отдельный контейнер; Nuclei — **встроен** в backend-образ.
- Очередь воркеров (`docs/mass-scale-tz.md`) — не реализовано.