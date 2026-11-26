# Процесс: правка → GitHub → сервер

После изменений в проекте агент в Cursor:

1. Вносит правки в код.
2. `git commit` + `git push` в `main`.
3. **Обязательно** сразу деплой на прод (если изменения для пользователей/API) — без отдельной просьбы заказчика.
4. Обновить **`PROGRESS.md`** (блок «Снимок продакшена» + `docs/prod-snapshot.md` при смене лимитов/инфры) и при необходимости ТЗ (`docs/outreach-machine-tz.md`).
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

Панель 50 сайтов (~2–4 ч): `REGRESSION_FILE=regression_urls_panel50.json bash .../vps-regression.sh`  
См. `docs/regression-panel.md`. Плановый прогон — cron на VPS (вс 01:30 / 1-е 01:15 MSK), не вручную в дневные часы.

Файл `.env` на сервере **не перезаписывается** при обычном деплое (`remote-redeploy.sh`).
Полная первичная установка — только `scripts/deploy-witty.sh` (создаёт `.env` один раз).