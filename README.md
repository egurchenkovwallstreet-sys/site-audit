# Сервис аудита сайтов

Веб-сервис для автоматизированной проверки сайтов: технические сигналы
безопасности и риски соответствия требованиям 152-ФЗ.

## Сервер — основная среда

Разработка и запуск на **VPS + Docker Compose** (PostgreSQL, API, фронт, Caddy).
На слабом ноуте достаточно Git и Cursor: правки → `git push` → на сервере
`git pull && docker compose up -d --build`.

Полная инструкция: **[docs/server-setup.md](docs/server-setup.md)**.

## Структура проекта

- `backend/` — API на Python и FastAPI.
- `frontend/` — приложение на Next.js и TypeScript.
- `scanner/` — интеграции изолированных сканеров.
- `docs/` — архитектурная и эксплуатационная документация.

## Требования

- Python 3.12+
- Node.js 20+
- npm 10+
- PostgreSQL: облачная БД, локальная установка **или** Docker (опционально)

На слабом ноутбуке Docker не нужен — см.
[docs/local-without-docker.md](docs/local-without-docker.md).

## Локальный запуск

Скопируйте `.env.example` в `.env` и задайте `DATABASE_URL` (облако или локальный Postgres).

### PostgreSQL (опционально через Docker)

```powershell
docker compose up -d db
```

Если Docker не используете — пропустите этот шаг и настройте БД по инструкции выше.

### Миграции

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
alembic upgrade head
```

Схема и таблицы описаны в [docs/database.md](docs/database.md).

### Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Проверка: `http://localhost:8000/api/health` и `http://localhost:8000/api/health/db`.
Документация API — `http://localhost:8000/docs`.

### Frontend

В отдельном терминале:

```powershell
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:3000`.

## Состояние разработки

Выполненные и проверенные задачи отмечаются в [PROGRESS.md](PROGRESS.md).  
Актуальный прод (лимиты, nginx, `.env` без секретов): [docs/prod-snapshot.md](docs/prod-snapshot.md).

Продолжение в новом чате Cursor — скопируйте [docs/NEW_CHAT_PROMPT.md](docs/NEW_CHAT_PROMPT.md).

План публикации на GitHub и деплоя — [docs/deployment.md](docs/deployment.md).
