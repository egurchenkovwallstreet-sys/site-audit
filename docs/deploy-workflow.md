# Процесс: правка → GitHub → сервер

После изменений в проекте агент в Cursor:

1. Вносит правки в код.
2. `git commit` + `git push` в `main`.
3. На **Witty Vulpecula** (`194.87.220.206`):
   ```bash
   ssh root@194.87.220.206 'bash /root/apps/site-audit/scripts/remote-redeploy.sh'
   ```
   (или `git pull` + `docker compose ... up -d --build`).

Сайт: **http://194.87.220.206:8080**

Файл `.env` на сервере **не перезаписывается** при обычном деплое (`remote-redeploy.sh`).
Полная первичная установка — только `scripts/deploy-witty.sh` (создаёт `.env` один раз).