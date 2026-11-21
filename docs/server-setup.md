# Сервер — основная среда разработки

Вся разработка ведётся на VPS: код на GitHub, на сервере `git pull` и
`docker compose up -d --build`. На ноуте Docker не нужен.

## 1. Подготовка VPS (Ubuntu 22.04/24.04)

Минимум: **2 vCPU, 4 GB RAM, 40 GB SSD** (для ZAP/Nuclei позже лучше 4–8 GB).

Подключение по SSH:

```bash
ssh user@SERVER_IP
```

На сервере один раз:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# перелогиньтесь в SSH
```

Или скопируйте на сервер и выполните `scripts/server-bootstrap.sh` из репозитория.

## 2. GitHub

1. Создайте репозиторий (приватный можно).
2. Локально или с ноута (без Docker):

```powershell
cd "C:\Users\User\Сервис проверки сайтов"
git add .
git commit -m "Initial: backend, frontend, docker compose for server"
git branch -M main
git remote add origin https://github.com/USER/REPO.git
git push -u origin main
```

3. На сервере:

```bash
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/USER/REPO.git site-audit
cd site-audit
```

Для приватного репо: deploy key или `gh auth login` на сервере.

## 3. Файл `.env` на сервере

```bash
cp .env.example .env
nano .env
```

Обязательно:

```env
POSTGRES_PASSWORD=<длинный_секрет>
SITE_ADDRESS=:80
# или с доменом: audit.example.ru

# Публичный URL без /api в конце — тот же хост, что открывает пользователь
NEXT_PUBLIC_API_URL=http://SERVER_IP
CORS_ORIGINS=http://SERVER_IP

# Когда будет домен и HTTPS:
# NEXT_PUBLIC_API_URL=https://audit.example.ru
# CORS_ORIGINS=https://audit.example.ru
```

Секреты GigaChat и ЮKassa добавите на шагах 6–8.

## 4. Запуск

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

Проверки:

- Сайт: `http://SERVER_IP/`
- API: `http://SERVER_IP/api/health`
- БД: `http://SERVER_IP/api/health/db`
- Swagger: `http://SERVER_IP/docs`

Миграции выполняются автоматически при старте `backend` (`alembic upgrade head`).

## 5. Как дальше менять код

**Вариант A — правки на ноуте + push (рекомендуется)**

1. Редактируете в Cursor локально (лёгкий ноут).
2. `git commit` → `git push`.
3. На сервере: `git pull && docker compose up -d --build`.

**Вариант B — Cursor Remote SSH**

1. Cursor → Remote SSH → подключиться к серверу.
2. Открыть папку `~/apps/site-audit`.
3. Правки сразу на сервере, коммиты в Git с сервера или с ноута.

**Вариант C — правки только по SSH**

`nano` / `vim` на сервере — возможно, но неудобно для больших фич.

## 6. Обновление после изменений

```bash
cd ~/apps/site-audit
git pull
docker compose up -d --build
# только backend:
# docker compose up -d --build backend
```

## 7. Домен и HTTPS

1. A-запись домена на IP сервера.
2. В `.env`: `SITE_ADDRESS=audit.example.ru`, обновить `NEXT_PUBLIC_API_URL` и `CORS_ORIGINS`.
3. `docker compose up -d --build` — Caddy получит Let's Encrypt (порт 443 открыт).

## 8. Сканеры ZAP/Nuclei

Подключаются на шаге 3 в `docker-compose.yml` только на сервере. Локально на ноуте не запускаются.

## Troubleshooting

```bash
docker compose logs backend
docker compose exec db psql -U site_audit -d site_audit -c '\dt'
```

Если не собирается frontend — на сервере нужно ~2 GB свободной RAM при `npm run build` в Docker.