# Разработка без Docker на ноутбуке

Docker Desktop на слабом ПК не обязателен. Для MVP достаточно:

| Компонент | На ноуте | На сервере (позже) |
|-----------|----------|---------------------|
| PostgreSQL | Облако или локальная установка | Свой инстанс или managed DB |
| Backend (FastAPI) | Да | Да |
| Frontend (Next.js) | Да | Да |
| OWASP ZAP / Nuclei | Нет (заглушка или отключено) | Docker или отдельные контейнеры |

Сканеры тяжёлые; их имеет смысл поднимать только на VPS при деплое, а локально
тестировать API, комплаенс по HTML и оплату.

## Вариант A (рекомендуется): облачная PostgreSQL

Бесплатные тарифы подходят для разработки:

- [Neon](https://neon.tech)
- [Supabase](https://supabase.com) → только Database, connection string
- [Railway](https://railway.app)

1. Создайте БД в панели провайдера.
2. Скопируйте connection string (часто `postgresql://...`).
3. В `.env` задайте:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Для Alembic драйвер подменится автоматически (`psycopg`).

4. Миграции:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

5. Проверка: `GET http://localhost:8000/api/health/db`.

## Вариант B: PostgreSQL без Docker на Windows

Один сервис PostgreSQL обычно легче, чем Docker Desktop.

1. Установите PostgreSQL 16 (официальный инсталлятор или `winget install PostgreSQL.PostgreSQL.16`).
2. В pgAdmin или `psql` создайте пользователя и БД:

```sql
CREATE USER site_audit WITH PASSWORD 'change_me';
CREATE DATABASE site_audit OWNER site_audit;
```

3. В `.env`:

```env
DATABASE_URL=postgresql+asyncpg://site_audit:change_me@localhost:5432/site_audit
```

4. `alembic upgrade head` — как выше.

Если порт `5432` занят другим PostgreSQL, смените порт в инсталляторе или
укажите другой порт в `DATABASE_URL`.

## Вариант C: Docker только на сервере

Файл `docker-compose.yml` в корне остаётся для VPS: там же позже можно добавить
ZAP/Nuclei. На ноуте этот файл можно не трогать.

## Локальная разработка сканеров (шаг 3+)

Пока нет сервера, в коде предусмотрим режим без ZAP/Nuclei (только
`compliance_checker` по HTTP и тестовые технические findings). Полное
сканирование включим через переменные окружения на сервере.

Планируемые переменные (добавим на шаге 3):

```env
SCANNER_ZAP_ENABLED=false
SCANNER_NUCLEI_ENABLED=false
```

На проде на VPS: `true` и URL до API ZAP в той же сети, что и backend.