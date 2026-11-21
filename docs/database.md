# База данных

PostgreSQL 16, схема из ТЗ:

| Таблица | Назначение |
|---------|------------|
| `users` | Пользователи (`active_subscription_id` — активная подписка) |
| `scans` | Запуски проверки (`access_level`: 0 бесплатно, 1 диагностика, 2 расширенный) |
| `findings` | Находки (`min_level`: 1 список, 2 рекомендации) |
| `payments` | Платежи за отчёт или подписку |
| `subscriptions` | Подписка 1490 ₽/мес |

Миграции: Alembic в `backend/alembic/`.

PostgreSQL без Docker: [local-without-docker.md](local-without-docker.md).

Через Docker (если есть):

```powershell
docker compose up -d db
```

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
alembic upgrade head
```

Проверка: `GET http://localhost:8000/api/health/db` → `database: connected`.