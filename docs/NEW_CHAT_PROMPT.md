# Промпт для нового чата — «Сервис проверки сайтов» (152-ФЗ)

Скопируйте блок **«Инструкция агенту»** в первое сообщение нового чата в Cursor.

---

## Инструкция агенту

Ты продолжаешь разработку **веб-сервиса автоматической проверки сайтов** на соответствие **152-ФЗ** и технических рисков (штрафы по справочнику КоАП). Рабочая папка: репозиторий **site-audit**.

### Обязательно прочитать перед работой (в этом порядке)

1. **`PROGRESS.md`** — что сделано, что в плане; **фаза A завершена**, **фаза B** — домен, безопасность, ЮKassa.
2. **`docs/launch-phase-b-tz.md`** — чеклисты запуска (B1–B4).
3. **`docs/compliance-legal-map.md`** — какие нормы 152-ФЗ → что ищем на сайте → штраф.
4. **`docs/deploy-workflow.md`** — деплой на VPS (после содержательных изменений кода).
5. **`docs/prod-snapshot.md`** — фактическая инфраструктура.
6. **`docs/report-policy.md`** — антибот, отчёты 490/990 ₽, гейт после ЮKassa.

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

### Фаза A (готово)

- Скан до **30** страниц, Playwright, Nuclei, комплаенс/SEO/security, честный scope.
- UI: таймер 10:00, все findings, мобильная вёрстка, HTML-отчёты с оформлением.
- Регрессия по cron; прод стабилен.

### Фаза B (текущая работа)

1. **B1** — домен, HTTPS, env URL, SEO (`docs/seo-setup.md`).
2. **B2** — rate limit, SSRF, заголовки, firewall (`PROGRESS.md` шаг 11).
3. **B3** — ЮKassa, webhook, гейт download, UI оплаты (`PROGRESS.md` шаг 8).
4. **B4** — финальная приёмка (`PROGRESS.md` шаг 12).

**Отложено:** GigaChat, подписка, масштаб (`docs/mass-scale-tz.md`), outreach (`docs/outreach-machine-tz.md`).

### Правила работы в Cursor (обязательны)

1. Минимальный diff; не ломать логику штрафов без обновления `compliance-legal-map.md`.
2. После итерации с кодом: `PROGRESS.md` → commit → push → `remote-redeploy.sh` (см. `.cursor/rules/deploy-after-work.mdc`).
3. Не трогать `.env` на сервере без явной задачи; не force push в `main`.
4. Проект «Система сигналов» — не менять без явного запроса.

### Первый шаг в новом чате

Ответь одной строкой: «Прочитал PROGRESS и launch-phase-b-tz; фаза B: …; следующий пункт: …» — затем выполняй задачу пользователя.

---

*Обновлено: 2026-11-27.*