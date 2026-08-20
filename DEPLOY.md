# Перенос и запуск на другом ПК

## Требования

- Docker Desktop или Docker Engine с Compose plugin.
- Открытые входящие порты `80` и `443` на ПК, где будет хоститься сервис.
- DNS A-запись домена должна указывать на внешний IP этого ПК/роутера.
- На роутере нужно пробросить порты `80` и `443` на локальный IP ПК.

## Подготовка

```bash
cp .env.example .env
```

В `.env` замените:

```env
APP_DOMAIN=bmrl.example.com
PUBLIC_BASE_URL=https://bmrl.example.com
CORS_ORIGINS=https://bmrl.example.com
CADDY_SITE_ADDRESS=bmrl.example.com
POSTGRES_PASSWORD=long-random-password
JWT_SECRET=another-long-random-secret
ADMIN_PASSWORD=strong-admin-password
```

Для входа через Steam `PUBLIC_BASE_URL` должен совпадать с внешним адресом сайта, потому что Steam вернёт пользователя на `PUBLIC_BASE_URL/api/auth/steam/callback`.

## Запуск

```bash
docker compose up --build -d
```

Проверка:

```bash
docker compose ps
docker compose logs -f backend
```

Адреса:

- сайт: `https://APP_DOMAIN`
- API: `https://APP_DOMAIN/api/docs`
- healthcheck: `https://APP_DOMAIN/health`

## Резервная копия PostgreSQL

```bash
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > bmrl_backup.sql
```

Восстановление:

```bash
docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB" < bmrl_backup.sql
```

## Автоматические бэкапы

Скрипт `scripts/weekly-backup.ps1` сохраняет PostgreSQL и загруженные файлы из `/api/uploads`, а затем оставляет только 3 последних успешных бэкапа.

Разовый запуск:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\weekly-backup.ps1
```

Поставить еженедельный запуск, по умолчанию воскресенье 03:00:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\weekly-backup.ps1 -InstallWeeklyTask
```

Поменять день, время или количество хранимых копий:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\weekly-backup.ps1 -InstallWeeklyTask -WeeklyDay Monday -At 04:00 -Keep 3
```

## HTTPS

HTTPS уже подключен через контейнер `caddy` в `docker-compose.yml`. Caddy автоматически получает и продлевает сертификат Let's Encrypt, если:

- `CADDY_SITE_ADDRESS` содержит домен без `http://` и `https://`;
- DNS A-запись домена указывает на белый IP этого ПК/роутера;
- порты `80` и `443` проброшены на ПК и не заняты другой программой;
- файрвол Windows разрешает входящие подключения на `80` и `443`.

Для локального запуска без сертификата оставьте:

```env
CADDY_SITE_ADDRESS=http://localhost
```
