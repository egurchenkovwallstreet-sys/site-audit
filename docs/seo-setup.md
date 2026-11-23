# SEO для нашего лендинга (site-audit)

Проверка **чужих** сайтов (блок «SEO и разметка») — это `seo_checker.py`. Здесь — продвижение **нашего** сервиса.

## Текущая техника в репозитории

| Элемент | Где |
|--------|-----|
| `title`, `description`, keywords, OG, Twitter, canonical | `frontend/src/app/layout.tsx` |
| `robots.txt` | `frontend/src/app/robots.ts` → `/robots.txt` |
| `sitemap.xml` | `frontend/src/app/sitemap.ts` → только главная |
| JSON-LD WebApplication | `layout.tsx` |
| `lang="ru"` | `<html lang="ru">` |

Базовый URL для метаданных: **`NEXT_PUBLIC_SITE_URL`** (в Docker — из `PUBLIC_SITE_URL`). После смены домена нужен **ребилд frontend**.

## Обязательно до ожиданий от поиска

1. **Домен + HTTPS** — индексация по голому IP слабая; в `.env` обновить `PUBLIC_SITE_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`, Caddy (`SITE_ADDRESS`).
2. **Яндекс Вебмастер** и **Google Search Console** — подтверждение домена, отправка `https://ваш-домен/sitemap.xml`.
3. **Проверка своим сканером** — прогнать главную, закрыть пункты в «SEO и разметка».

## Контент (следующие шаги, не в коде)

- H1 на главной с ключами: *152-ФЗ*, *аудит*, *уязвимости* (не только «до 10 минут»).
- Отдельные страницы под запросы: «проверка cookie», «аудит 152-ФЗ», «168-ФЗ на сайте» — каждая со своим `metadata` и URL в `sitemap.ts`.
- FAQ на главной (что проверяем, что не юрзаключение, лимит страниц).
- **og:image** — положить `frontend/public/og-image.png` (1200×630) и добавить `openGraph.images` в `layout.tsx`.

## Аналитика

- Яндекс.Метрика / GA4 — отдельный счётчик в `layout` (не путать с SEO-сканером клиентов).

## Страницы результатов скана

Сейчас одна SPA-страница без URL `/check/:id` — индексируется только главная. Если позже появятся публичные URL отчётов — ставить **`noindex`** для личных результатов.

## Чеклист после выхода на домен

- [ ] `NEXT_PUBLIC_SITE_URL=https://…` + redeploy
- [ ] `curl -s https://домен/robots.txt` и `/sitemap.xml`
- [ ] View-source: title, description, canonical, JSON-LD
- [ ] Вебмастер + Search Console
- [ ] Свой скан → SEO-findings = 0 или объяснимые исключения