# Регрессия: строгий набор и панель из 50 сайтов

## Файлы

| Файл | Назначение | Время (VPS) |
|------|------------|-------------|
| `scripts/regression_urls.json` | **9 строгих** кейсов (эталоны, ловушки антибота/форм) | ~10–20 мин |
| `scripts/regression_urls_panel50.json` | **50 разнотипных** URL + те же 9 строгих | **~2–4 ч** |

## Smoke-кейсы

Записи с тегом `smoke` **без жёстких `expect`**: скан должен **завершиться без падения** (compliance + security). Findings могут быть любыми — цель панели: разнообразие типов сайтов и отлов крашей/таймаутов при массовом прогоне.

Тег `strict` — по-прежнему сверка `expect` (политика, антибот, формы).

## Запуск

```bash
# VPS, строгий набор
bash scripts/vps-regression.sh

# VPS, панель 50 (долго)
bash scripts/vps-regression.sh --file /tmp/regression_urls_panel50.json
# предварительно docker cp panel50 в контейнер — скрипт копирует только regression_urls.json;
# для панели:
docker cp scripts/regression_urls_panel50.json $(docker compose ps -q backend):/tmp/regression_urls_panel50.json
docker compose exec -T backend python /tmp/regression_scan.py --file /tmp/regression_urls_panel50.json
```

Локально (нужен Playwright): `py scripts/regression_scan.py --file scripts/regression_urls_panel50.json`

## Категории в панели

Банки, маркетплейсы, медиа, госсектор, образование, авто, медицина, retail, телеком, хостинг, сервисы, SMB/SPA, antibot, HTTP baseline.

Перед приёмкой релиза достаточно **строгого набора**; панель — раз в спринт или после крупных изменений движка.