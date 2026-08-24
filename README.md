# BMRL Race Control

Многопользовательская система для создания, редактирования, отслеживания и модерирования гонок по ТЗ BMRL v3.0.

## Что входит

- FastAPI REST API, JWT, роли `admin`, `moder`, `marshall`, `smm`, `pilot`.
- PostgreSQL с async SQLAlchemy, индексами и пулом соединений.
- Redis storage для SlowAPI, чтобы лимиты были общими для всех Gunicorn workers.
- SlowAPI rate limiting: по умолчанию `3/minute` для каждого endpoint, админский токен освобожден от лимита.
- Vue 3 SPA с `vue-i18n`, светлой/темной темой через CSS variables и сохранением выбора в `localStorage`.
- Docker Compose для переноса на другой ПК: PostgreSQL, backend и Nginx со статикой SPA и reverse proxy на `/api`.

## Быстрый запуск

1. Скопируйте переменные:

```bash
cp .env.example .env
```

2. В `.env` поменяйте пароли, `JWT_SECRET` и домен:

```env
APP_DOMAIN=your-domain.example
WEB_PORT=80
PUBLIC_BASE_URL=http://your-domain.example
CORS_ORIGINS=http://your-domain.example
```

3. Запустите сервис:

```bash
docker compose up --build -d
```

4. Откройте:

- Web локально: `http://localhost`
- Web на домене: `http://APP_DOMAIN` (или `:8080`, если `WEB_PORT=8080`)
- API healthcheck: `/health`
- API docs: `/api/docs`

Для локального запуска без домена оставьте `APP_DOMAIN=localhost`, `WEB_PORT=80`, `PUBLIC_BASE_URL=http://localhost`, `CORS_ORIGINS=http://localhost,http://127.0.0.1` и откройте `http://localhost`.

Подробная памятка по переносу на другой ПК и домену лежит в `DEPLOY.md`.

## Выгрузка на ПК с белым IP и портом 8080

1. На ПК, где будет работать сайт, установите Docker Desktop или Docker Engine с Compose plugin.

2. Пробросьте на роутере порт на локальный IP этого ПК:

```text
8080 -> ПК:8080
```

3. В DNS домена создайте A-запись на белый IP:

```text
your-domain.example -> ваш белый IP
```

4. Скопируйте проект на этот ПК и создайте `.env`:

```bash
cp .env.example .env
```

5. В `.env` укажите домен и публичный HTTP-адрес:

```env
APP_DOMAIN=your-domain.example
WEB_PORT=8080
PUBLIC_BASE_URL=http://your-domain.example:8080
CORS_ORIGINS=http://your-domain.example:8080
```

Также обязательно замените `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET` и `ADMIN_PASSWORD` на свои значения. Пароль в `DATABASE_URL` должен совпадать с `POSTGRES_PASSWORD`.

6. Запустите весь проект одной командой:

```bash
docker compose up --build -d
```

Проверка после запуска:

```bash
docker compose ps
docker compose logs -f backend
```

Адреса после успешного запуска:

- сайт: `http://your-domain.example:8080`
- healthcheck: `http://your-domain.example:8080/health`
- API docs: `http://your-domain.example:8080/api/docs`

## Производительность

Настройки под 500 одновременных пользователей и около 3000 зарегистрированных аккаунтов:

- backend запускается через Gunicorn + Uvicorn workers (`WEB_CONCURRENCY=4`);
- async драйвер PostgreSQL `asyncpg`;
- пул БД `DB_POOL_SIZE=15`, `DB_MAX_OVERFLOW=20`;
- PostgreSQL `max_connections=200`;
- критичный сценарий регистрации на гонку использует row lock (`SELECT ... FOR UPDATE`), чтобы не терять заявки при параллельных запросах;
- списки читаются с пагинацией;
- для частых фильтров и JSONB-полей добавлены индексы.

## Разработка

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev --host 0.0.0.0
```
