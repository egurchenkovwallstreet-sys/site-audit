# Деплой и GitHub

Актуальный runbook: **[server-setup.md](server-setup.md)** (сервер как основная среда).

## Репозиторий GitHub

1. Создать приватный или публичный репозиторий на GitHub.
2. Закоммитить проект (без `.env`, без `backend/.venv/`, без `frontend/node_modules/`).
3. Добавить remote и выполнить `git push -u origin master` (или `main`).

Рекомендуется GitHub Actions для lint/backend tests (позже).

## Сервер

Минимальный прод-стек:

- Docker Compose на VPS (не на слабом ноуте): PostgreSQL при необходимости,
  backend, frontend, ZAP/Nuclei — или managed PostgreSQL + только сканеры в Docker.
- Обратный прокси (Caddy или nginx) с TLS.
- Переменные окружения из секретов хостинга (не из репозитория).
- `DATABASE_URL`, ключи GigaChat, ЮKassa, `NEXT_PUBLIC_API_URL` на публичный API.

Детальный runbook добавим после шагов 3–8 (сканеры, платежи, фронтенд).