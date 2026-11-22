# Промпт для нового чата — «Сервис проверки сайтов» (152-ФЗ)

Скопируйте блок **«Инструкция агенту»** в первое сообщение нового чата в Cursor.

---

## Инструкция агенту

Ты продолжаешь разработку **веб-сервиса автоматической проверки сайтов** на соответствие **152-ФЗ** и технических рисков (штрафы по справочнику КоАП). Рабочая папка: репозиторий **site-audit**.

### Обязательно прочитать перед работой (в этом порядке)

1. **`PROGRESS.md`** — что сделано, что в плане, итерации (источник истины по статусу).
2. **`docs/compliance-legal-map.md`** — какие нормы 152-ФЗ → что ищем на сайте → штраф.
3. **`docs/deploy-workflow.md`** — деплой на VPS (обязателен после каждой содержательной итерации).
4. **`docs/architecture.md`**, **`docs/database.md`** — при изменении API/БД.
5. **`docs/deployment.md`**, **`docs/server-setup.md`** — при смене инфраструктуры.
6. **`README.md`** — структура `backend/`, `frontend/`, `scanner/`.

Не выдумывай штрафы и нормы: опирайся на `backend/app/data/penalties.py`, `legal_basis.py`, карту в `compliance-legal-map.md`.

### Исходные данные

| Параметр | Значение |
|----------|----------|
| Репозиторий | https://github.com/egurchenkovwallstreet-sys/site-audit |
| Ветка | `main` |
| Прод (UI + API) | http://194.87.220.206:8080 |
| VPS | `root@194.87.220.206`, проект на сервере: `/root/apps/site-audit` |
| Деплой | `ssh root@194.87.220.206 "bash /root/apps/site-audit/scripts/remote-redeploy.sh"` |
| Стек | FastAPI (Python 3.12), Next.js, PostgreSQL 16, Docker Compose |
| Ключевые модули | `backend/app/compliance/` — checker, privacy_detection, form_consent, spa_bundle_scan; `backend/app/scan/` — page_fetch, site_scan, site_pages; `frontend/src/components/ScanResults.tsx` |
| Регрессия | `scripts/regression_urls.json`, `scripts/regression_scan.py` |
| Эталоны | Darom SPA, example.com, okno.ru (формы), cian.ru (антибот/sitemap) |

**Приоритет продукта (согласовано с заказчиком):** сначала **качество проверки и UX**, потом GigaChat/отчёты, потом платежи.

### Что уже сделано (кратко)

- API сканов: POST `/api/scans`, findings, **`context`** (политика, cookie, страницы, scope).
- Мульти-страница: до **15 URL** (вход, ссылки, sitemap); исключены **sitemap `*.xml.gz`** как «страницы».
- Антибот: fallback `/contacts/`, тип **`access`** (не факт 152-ФЗ); честный UI при `pages_checked = 0`.
- Политика ПДн: **строгий** детектор (без ложных «152-ФЗ в meta»); для ЦИАН — **`back_location`** в заглушке Servicepipe; сиды `/legal-documents/…`.
- Формы: штраф только при полях ПДн; исключены поиск/логин; okno без ложных «7 форм».
- Cookie/иностранные SDK: только при **реальной** аналитике в HTML/скриптах.
- SPA: один проход JS-бандлов (`analyze_spa_bundles`).
- UI: шаги скана, «Что проверили», факты vs прогноз (security), цвета штрафов.
- VPS: многократные деплои; проверки okno.ru, cian.ru, self-scan.

Детали и галочки — только в **`PROGRESS.md`**.

Последние значимые коммиты на `main` (ориентир): `adef2e0` (ЦИАН/sitemap, back_location), `0ad4627` (строгая политика), `7848185` (антибот/access).

### Что предстоит (фаза A, по ТЗ / PROGRESS)

1. **Playwright** — читать HTML на антибот/SPA (ЦИАН, etagi, attik), не только `back_location`.
2. **Регрессия** — полный прогон на VPS, расширить `regression_urls.json` (ЦИАН, Авито, «плохой» сайт).
3. **Содержание политики** — ч.4 ст. 18.1 (оператор, цели, права), когда текст стабильно доступен.
4. Техника: Referrer-Policy, доработка Set-Cookie; позже ZAP/Nuclei.
5. **Приёмка UI** заказчиком на сервере.
6. Юрист: верификация формулировок КоАП.

**Отложено (фаза B):** GigaChat, уровни отчётов, ЮKassa, подписка, шаги 11–12 безопасность/финал.

### Правила работы в Cursor (обязательны)

1. Минимальный diff; не ломать согласованную логику штрафов без обновления `compliance-legal-map.md`.
2. После **завершённой** итерации (код проверен, имеет смысл на проде):
   - обновить **`PROGRESS.md`** (поставить `[x]` только если проверили на VPS или регрессией);
   - `git add` релевантные файлы → `git commit` → `git push origin main`;
   - **`ssh root@194.87.220.206 "bash /root/apps/site-audit/scripts/remote-redeploy.sh"`**;
   - при необходимости — тестовый скан через API (`POST http://194.87.220.206:8080/api/scans`) и кратко зафиксировать id скана в PROGRESS или в ответе пользователю.
3. Не трогать `.env` на сервере; не делать force push в `main`.
4. Отдельный проект заказчика: «Система сигналов» (paper-short, фильтры 152-ФЗ) — **не менять**, если пользователь явно не просит.

### Как проверять

```powershell
# Создать скан
Invoke-RestMethod -Method POST -Uri 'http://194.87.220.206:8080/api/scans' `
  -ContentType 'application/json' -Body '{"target_url":"https://example.com/"}'
# GET /api/scans/{id} и /api/scans/{id}/findings
```

### Первый шаг в новом чате

Ответь одной строкой: «Прочитал PROGRESS и compliance-legal-map; текущая фаза: …; следующий пункт: …» — затем выполняй задачу пользователя.

---

*Файл обновлять при смене фазы или инфраструктуры. Дата последнего обновления: 2026-11-22.*