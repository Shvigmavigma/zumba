# BRML Race Control

Многопользовательская система для создания, редактирования, отслеживания и модерирования гонок по ТЗ BRML v3.0.

## Что входит

- FastAPI REST API, JWT, роли `admin`, `moder`, `marshall`, `smm`, `pilot`.
- PostgreSQL с async SQLAlchemy, индексами и пулом соединений.
- Redis storage для SlowAPI, чтобы лимиты были общими для всех Gunicorn workers.
- SlowAPI rate limiting: по умолчанию `3/minute` для каждого endpoint, админский токен освобожден от лимита.
- Vue 3 SPA с `vue-i18n`, светлой/темной темой через CSS variables и сохранением выбора в `localStorage`.
- Docker Compose для переноса на другой ПК: PostgreSQL, backend, Nginx со статикой SPA и reverse proxy на `/api`.

## Быстрый запуск

1. Скопируйте переменные:

```bash
cp .env.example .env
```

2. В `.env` поменяйте пароли, `JWT_SECRET` и домен:

```env
APP_DOMAIN=your-domain.example
PUBLIC_BASE_URL=http://your-domain.example
CORS_ORIGINS=http://your-domain.example
```

3. Запустите сервис:

```bash
docker compose up --build -d
```

4. Откройте:

- Web: `http://APP_DOMAIN`
- API healthcheck: `http://APP_DOMAIN/health`
- API docs: `http://APP_DOMAIN/api/docs`

Для локального запуска без домена оставьте `APP_DOMAIN=localhost` и откройте `http://localhost`.

Подробная памятка по переносу на другой ПК и домену лежит в `DEPLOY.md`.

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
