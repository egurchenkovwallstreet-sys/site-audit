# Процесс: правка → GitHub → сервер

После изменений в проекте агент в Cursor:

1. Вносит правки в код.
2. `git commit` + `git push` в `main`.
3. **Обязательно** сразу деплой на прод (если изменения для пользователей/API) — без отдельной просьбы заказчика.
4. Обновить **`PROGRESS.md`** и при необходимости ТЗ (`docs/outreach-machine-tz.md`).
5. На **Witty Vulpecula** (`194.87.220.206`):
   ```bash
   ssh root@194.87.220.206 'bash /root/apps/site-audit/scripts/remote-redeploy.sh'
   ```
   (или `git pull` + `docker compose ... up -d --build`).

Сайт: **http://194.87.220.206:8080**

После крупных изменений сканера (по желанию, ~10–20 мин на VPS):

```bash
ssh root@194.87.220.206 'bash /root/apps/site-audit/scripts/vps-regression.sh'
```

Один кейс: `.../vps-regression.sh --case Darom`

Файл `.env` на сервере **не перезаписывается** при обычном деплое (`remote-redeploy.sh`).
Полная первичная установка — только `scripts/deploy-witty.sh` (создаёт `.env` один раз).