from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.db import SessionLocal, db_initialization_lock, init_db
from app.rate_limit import limiter
from app.routers import appeals, auth, banners, dashboard, hall_of_fame, news, penalties, race_assets, races, setups, teams, twitch, users
from app.seed import seed_defaults


settings = get_settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        async with db_initialization_lock():
            await init_db()
            async with SessionLocal() as session:
                await seed_defaults(session)
    yield


app = FastAPI(
    title=settings.app_name,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: ORJSONResponse({"detail": "Rate limit exceeded"}, status_code=429))
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/api/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(races.router, prefix="/api/races", tags=["races"])
app.include_router(race_assets.router, prefix="/api/race-assets", tags=["race-assets"])
app.include_router(penalties.router, prefix="/api/penalties", tags=["penalties"])
app.include_router(appeals.router, prefix="/api/appeals", tags=["appeals"])
app.include_router(banners.router, prefix="/api/banners", tags=["banners"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(setups.router, prefix="/api/setups", tags=["setups"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(hall_of_fame.router, prefix="/api/hall-of-fame", tags=["hall-of-fame"])
app.include_router(twitch.router, prefix="/api/twitch", tags=["twitch"])
