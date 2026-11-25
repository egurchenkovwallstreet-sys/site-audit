# Прогресс разработки

Обновляется только после реализации и проверки каждого пункта.

## Фаза A — качество проверки и UX (без оплаты и GigaChat)

### Итерация 1 (2025-11-21)

- [x] SPA: один проход по JS-бандлам (`analyze_spa_bundles`), без двойной загрузки.
- [x] Иностранные SDK: поиск только в `script`/`iframe`, не в CSP meta.
- [x] Политика ПДн: дополнительный разбор `sitemap.xml`.
- [x] Контекст проверки в API (`context`: политика, согласие, источник, scope).
- [x] Миграция `scans.context_json`.
- [x] Скан завершается успешно даже без находок (не падает на «пустом» отчёте).
- [x] UI: шаги прогресса, блок «Что проверили», зелёный баннер при чистом 152-ФЗ.
- [x] Главная: убрана реклама подписки, добавлено пояснение scope.
- [x] `scripts/regression_urls.json` + `scripts/regression_scan.py`.
- [x] Прогон регрессии на VPS после деплоя (Darom + example.com).
- [ ] Пользовательская проверка UI на сервере.

### Итерация 1.5 — строгая политика ПДн (2025-11-21)

- [x] Убраны ложные срабатывания: «152-ФЗ» в meta, слова «политика ПДн» на лендинге.
- [x] «Найдена» только: текст документа (≥500 зн., юр. формулировки), проверенная страница по ссылке, SPA с маршрутом/текстом политики.
- [x] Тест `backend/tests/test_privacy_detection.py`.
- [x] Self-scan на VPS: политика не «найдена» по маркетингу; штраф «нет политики» на лендинге сервиса.
- [x] okno.ru на VPS (API): политика на `/politika-konfidencialnosti`, факты по формам/SDK.
- [x] Полная регрессия `regression_scan.py` на VPS после всех правок.

### Итерация 1.5.1 — sitemap и крупные сайты (ЦИАН) (2025-11-22)

- [x] Исключены `*.xml.gz` и sitemap из списка «проверенных страниц» (не HTML).
- [x] Сиды обхода: `/legal-documents/`, типовые пути политики до sitemap.
- [x] Политика на антиботе: подтверждение по `back_location` (Servicepipe), без чтения текста.
- [x] Тесты `test_sitemap_scan.py`, дополнение `test_privacy_detection.py`.
- [x] cian.ru на VPS: `privacy_found`, без ложного штрафа за отсутствие политики.

### Итерация 1.4.1 — ложный антибот (2025-11-21)

- [x] Убраны широкие маркеры (антибот в тексте политики); отдельный тип `access`, не «факт 152-ФЗ».
- [x] Пояснение при HTTP 200 + заглушка/пустое тело.
- [x] UI: зелёный «без штрафов» только если `pages_checked > 0`; при антиботе — «не проверяли», не «не обнаружена».
- [x] Контекст при недоступном HTML: `privacy_found` / `consent_found` = `null`.

### Итерация 1.4 — мульти‑страница (2025-11-21)

- [x] До **15** внутренних URL: точка входа, ссылки с неё, sitemap.
- [x] Комплаенс по всем страницам (формы, аналитика, политика).
- [x] UI: счётчик и раскрываемый список проверенных страниц.
- [x] Playwright для сайтов, где все 15 URL — капча (Chromium, бюджет 8 URL; bootstrap по back_location и legal seeds)..

### Итерация 1.3 — обход антибота (2025-11-21)

- [x] Fallback `/contacts/`, `/contact/`, `/kontakty/` при 403/429/странице‑капче.
- [x] В контексте скана: `requested_url`, `scanned_url`, `used_fallback`.
- [x] Прогон etagi.com на VPS (регрессия, без ложного `no_privacy_policy`).

### Итерация 1.2 — привязка к нормам (2025-11-21)

- [x] `docs/compliance-legal-map.md` — матрица «152-ФЗ → что на сайте → КоАП».
- [x] `legal_basis.py` — преамбула в каждом факте (норма + что проверяли).
- [x] Cookie/баннер только при **реальной аналитике**, не «всегда».
- [x] Иностранные SDK только **аналитика/реклама** (не Firebase/CSP/jquery).
- [ ] Юрист: финальная верификация формулировок статей КоАП.

### Итерация 1.1 (2025-11-21)

- [x] Формы: штраф только если есть поля ПДн; исключены поиск, вход, служебные POST.
- [x] Согласие в SPA: не учитываем vendor-скрипты (jQuery и т.п.).
- [x] Чекбоксы `agreed` / consent; дедуп копий форм на странице (okno.ru).
- [x] okno.ru в регрессии на VPS (без ложного «7 форм без согласия»).

### Итерация 2 — Playwright (2025-11-22)

- [x] Chromium в backend (`mcr.microsoft.com/playwright/python:v1.49.1-jammy`), `playwright_fetch.py`, бюджет 8 URL.
- [x] Fallback при антиботе: bootstrap по `back_location` + legal seeds; повтор для юр. URL без текста политики.
- [x] Контекст: `playwright_urls`; тесты `test_playwright_integration.py`.
- [x] VPS: cian.ru scan **#173** — `privacy_found`, ~31 с (браузерные попытки); текст политики с IP дата-центра по-прежнему не отдаётся — остаётся `back_location`.
- [x] Полная регрессия `regression_scan.py` на VPS (Darom, example, okno, cian, etagi — OK, ~3 мин).

### Итерация 2 (продолжение)

- [x] Playwright для «пустых» SPA-оболочек и жёсткого антибота (полный текст политики, не только `back_location`).
- [x] Cookie / Referrer-Policy / Set-Cookie флаги (Referrer-Policy, HttpOnly, SameSite, Secure).
- [x] Расширение `regression_urls.json`: beautysova, avito, attik, neverssl (HTTP); полный прогон compliance+security.
- [x] `scripts/vps-regression.sh` — регрессия в backend-контейнере на VPS.
- [x] `scripts/regression_urls_panel50.json` — панель из **50** сайтов (smoke + 9 strict), `docs/regression-panel.md`.
- [x] Плановая регрессия: `scheduled-regression.sh` + cron (вс 01:30 strict, 1-е число 01:15 panel, окно 1–3 MSK).
- [x] Содержательная проверка политики (ч.4 ст. 18.1) — `privacy_policy_incomplete` (волна A1).
- [x] VPS 2025-11-22: Darom, okno, attik, cian — OK через `vps-regression.sh` (полный набор — по `deploy-workflow.md`).

---

## Шаг 1. Инициализация проекта

- [x] Создана структура `backend/`, `frontend/`, `scanner/`, `docs/`.
- [x] Создан файл `PROGRESS.md`.
- [x] Создан `README.md` с инструкцией локального запуска.
- [x] Создан `.env.example` с переменными приложения, БД, GigaChat и ЮKassa.
- [x] Backend и frontend запускаются локально, стартовые страницы доступны.

## Шаг 2. База данных и модели

- [x] Спроектирована схема БД (users, scans, findings, payments, subscriptions).
- [x] SQLAlchemy-модели и `access_level` / `min_level`.
- [x] Миграции Alembic (`backend/alembic/versions/20251121_0001_initial_schema.py`).
- [x] Миграция `context_json` для scans (`20251121_0002_scan_context.py`).
- [x] Docker Compose с PostgreSQL на сервере.
- [x] Проверено на VPS: `alembic upgrade` + `/api/health/db`.
- [x] Миграция `findings.penalty_code` + API (стабильная регрессия по кодам).

## Шаг 3. Интеграция сканеров

- [x] Пассивные тех. проверки (HTTPS, заголовки, утечки Server).
- [x] SPA-бандлы Flutter/JS для политики и согласия (`spa_bundle_scan.py`).
- [ ] ZAP/Nuclei на сервере (полный активный скан — позже).

## Шаг 4. Комплаенс-проверки

- [x] `backend/app/compliance/checker.py` — политика, cookie, формы, иностранные SDK.
- [x] **Глубина A1–A3** (`docs/scan-depth-roadmap.md`): политика ч.4, техзаголовки, трекеры; формы/реквизиты; обход контактов и legal-URL; при баннере — раскрытие cookie (`cookie_policy_*`).
- [x] **B0 security**: пассивные пробы типовых утечек (`.git`, `.env`, …) и mixed content на HTTPS-страницах.
- [x] **B1 / бюджет 10 мин**: Nuclei в скане, 22 стр., Playwright 14, CORS/COOP/CORP, UI «до 10 мин».
- [x] **168-ФЗ + SEO**: `fz168_checker.py`, `seo_checker.py`, блок UI «SEO и разметка».
- [x] **SEO лендинга**: metadata/OG/JSON-LD, `app/robots.ts`, `app/sitemap.ts`, `docs/seo-setup.md`, `NEXT_PUBLIC_SITE_URL`.
- [x] Скачивание отчётов HTML: кнопки на `/check/{id}`, API `paid-report/download` (short/extended), печать в PDF в браузере.
- [x] Зависания: лимит `asyncio.wait_for` на скан, stale → failed, `POST /restart`, UI доп. таймер + автоперезапуск.
- [ ] **Оплата и PDF-сервер** (фаза B): ЮKassa, гейт перед скачиванием (см. `docs/report-policy.md`).
- [x] robots.txt + sitemap.xml в поиске политики.
- [x] Привязка штрафов из справочника.
- [x] API: POST `/api/scans`, GET findings, контекст в GET scan.
- [x] Darom (`https://darom-app.online/`) — без ложных политика/cookie (проверено на VPS).
- [x] E-mail из Flutter-бандла (`main.dart.js`), в т.ч. Darom — `email_discover.py` + кэш SPA-скана.
- [x] Таймер 3–5 мин на экране скана, ускорение при раннем `completed` (деплой `b4f0132`).
- [x] Кнопка «Отправить письмо» + API preview outreach (`docs/smtp-setup.md`).
- [x] Базовый прогон `regression_scan.py` на VPS.

## Шаг 5. Справочник штрафов

- [x] `backend/app/data/penalties.py` + цвета и remediation.
- [x] Штрафы в UI: ИП / юрлицо / повторное по ст. 13.11 (`koap_sanctions.py`, таблица в отчёте).
- [ ] Проверено на сервере набором эталонных URL.

## Политика отчётов (согласовано)

- [x] `docs/report-policy.md`, `.cursor/rules/report-antibot-policy.mdc` — антибот, честный scope, отчёты 990/1990 только после оплаты.
- [x] Фаза A: на экране проверки все findings (подпись на форме).
- [ ] Paywall превью vs полный отчёт (фаза B, ЮKassa).

## Шаг 6. Интеграция GigaChat

- [ ] Отложено (после фазы A).

## Шаг 7. Отчёты и уровни доступа

- [ ] Отложено (после фазы A).

## Шаг 8. Платежи

- [ ] Отложено.

## Шаг 8.5. Подписка

- [ ] Отложено.

## Шаг 9. Главная страница

- [x] Главная с полем URL и кнопкой «Проверить» (Apple-стиль, тёмная тема).
- [x] Блок срочности на главной: риски КоАП, РКН, оффер и дисклеймер (`HomePitch`).
- [x] Страница результата `/check/[id]` (шаринг, noindex, опрос API).
- [x] Цветовая шкала штрафов и рисков в списке находок (green / yellow / red).
- [x] Факты / прогноз, масштаб UI +20%, scope на главной.
- [ ] Проверено пользователем на сервере после итерации 1.

## Шаг 10. Страница отчёта

- [ ] Отложено (расширенный отчёт — после GigaChat).

## Шаг 11. Безопасность и ограничения

- [ ] Не начат.

## Шаг 12. Финальная проверка

- [ ] Не начат.

## Масштабирование (реклама, ≥20 параллельных сканов)

- [ ] ТЗ согласовано: `docs/mass-scale-tz.md` (очередь, воркеры, M1–M4).
- [ ] Не начата реализация.

## Фаза C — «Машина уведомлений» (Outreach)

**Старт только после полноценного запуска основного сервиса** (стабильный прод, приёмка фазы A; желательно готова монетизация из фазы B).

- [ ] ТЗ согласовано: `docs/outreach-machine-tz.md`
- [ ] Не начата реализация