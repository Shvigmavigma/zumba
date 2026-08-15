# Перенос и запуск на другом ПК

## Требования

- Docker Desktop или Docker Engine с Compose plugin.
- Открытый входящий порт `80` на ПК, где будет хоститься сервис.
- DNS A-запись домена должна указывать на внешний IP этого ПК/роутера.
- На роутере нужно пробросить порт `80` на локальный IP ПК.

## Подготовка

```bash
cp .env.example .env
```

В `.env` замените:

```env
APP_DOMAIN=bmrl.example.com
PUBLIC_BASE_URL=http://bmrl.example.com
CORS_ORIGINS=http://bmrl.example.com
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

- сайт: `http://APP_DOMAIN`
- API: `http://APP_DOMAIN/api/docs`
- healthcheck: `http://APP_DOMAIN/health`

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

Текущий compose готовит сервис под HTTP-домен. Для HTTPS проще всего поставить Caddy или Nginx Proxy Manager перед этим compose и проксировать домен на порт `80` контейнера `web`.
