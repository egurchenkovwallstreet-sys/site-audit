# Подключение домена (Reg.ru) к site-audit

Пример: **audit152fz.online** → VPS **194.87.220.206**.

Кнопку Reg.ru **«Подключить»** (конструктор/хостинг) **не нажимайте** — у нас свой сервер и Docker.

---

## 1. DNS в Reg.ru

1. **Домены** → `audit152fz.online` → **Управление доменом** (или «DNS» / «Ресурсные записи»).
2. DNS-серверы: по умолчанию **ns1.reg.ru, ns2.reg.ru** — оставляем.
3. Добавьте записи:

| Тип | Имя (поддомен) | Значение |
|-----|----------------|----------|
| **A** | `@` (или пусто) | `194.87.220.206` |
| **A** | `www` | `194.87.220.206` |

4. Сохраните. Подождите **15–120 минут**.
5. Проверка с ПК: `nslookup audit152fz.online` → должен быть IP **194.87.220.206**.

Уведомление про «данные администратора» — для **.ru/.рф** и Госуслуги; для **.online** при необходимости заполните данные в кабинете Reg.ru отдельно.

---

## 2. Nginx на VPS (после появления DNS)

На сервере (из каталога проекта после `git pull`):

```bash
sudo mkdir -p /var/www/certbot
sudo cp deploy/nginx-site-audit-domain.conf /etc/nginx/sites-available/site-audit-domain
sudo ln -sf /etc/nginx/sites-available/site-audit-domain /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Сайт временно откроется по **http://audit152fz.online** (порт 80, без конфликта с ai-aggregator на `server_name _`).

---

## 3. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx   # если ещё нет
sudo certbot --nginx -d audit152fz.online -d www.audit152fz.online \
  --non-interactive --agree-tos -m ВАШ_EMAIL --redirect
```

Проверка: **https://audit152fz.online/**

---

## 4. `.env` на сервере (без git)

В `/root/apps/site-audit/.env`:

```env
PUBLIC_SITE_URL=https://audit152fz.online
NEXT_PUBLIC_API_URL=https://audit152fz.online
CORS_ORIGINS=https://audit152fz.online
PAYMENT_RETURN_URL=https://audit152fz.online
```

Пересборка фронта:

```bash
cd /root/apps/site-audit
bash scripts/remote-redeploy.sh
```

---

## 5. Чеклист

- [ ] DNS A на VPS
- [ ] nginx `site-audit-domain`
- [ ] certbot HTTPS
- [ ] `.env` + redeploy
- [ ] `docs/seo-setup.md` — вебмастер, sitemap

Старый адрес **http://194.87.220.206:8080** можно оставить для отладки.

*Домен в конфиге: `deploy/nginx-site-audit-domain.conf` — замените `server_name`, если смените домен.*