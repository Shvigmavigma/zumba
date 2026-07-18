from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user
from app.models import Role, User, UserStatus
from app.rate_limit import limiter
from app.schemas import LoginRequest, TokenResponse, UserPrivate, UserRegister
from app.security import create_access_token, hash_password, verify_password


router = APIRouter()
settings = get_settings()


def login_redirect(**params: str) -> RedirectResponse:
    query = urlencode(params)
    return RedirectResponse(f"{settings.public_base_url.rstrip('/')}/login?{query}", status_code=302)


@router.post("/register", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(payload: UserRegister, request: Request, session: AsyncSession = Depends(get_session)):
    duplicate = await session.scalar(
        select(User).where(
            or_(
                User.login == payload.login,
                User.email == payload.email,
                User.pilot_number == payload.pilot_number,
                User.steam_id == payload.steam_id,
            )
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Login, email, pilot number or Steam ID already exists")

    user = User(
        login=payload.login,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        nickname=payload.nickname,
        pilot_number=payload.pilot_number,
        country=payload.country,
        sr=5.0,
        discord=payload.discord,
        steam_id=payload.steam_id,
        role=Role.pilot,
        status=UserStatus.unapproved,
        avatar_color=payload.avatar_color,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("3/minute")
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(or_(User.login == payload.login, User.email == payload.login)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user), user=UserPrivate.model_validate(user))


@router.get("/steam/start")
@limiter.limit("3/minute")
async def steam_start(request: Request):
    base_url = settings.public_base_url.rstrip("/")
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{base_url}/api/auth/steam/callback",
        "openid.realm": base_url,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return RedirectResponse(f"{settings.steam_openid_url}?{urlencode(params)}", status_code=302)


@router.get("/steam/callback")
@limiter.limit("3/minute")
async def steam_callback(request: Request, session: AsyncSession = Depends(get_session)):
    params = dict(request.query_params)
    if params.get("openid.mode") != "id_res":
        return login_redirect(steam_error="Steam authentication was cancelled")

    verify_payload = params.copy()
    verify_payload["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(settings.steam_openid_url, data=verify_payload)
    if "is_valid:true" not in response.text:
        return login_redirect(steam_error="Steam authentication failed")

    claimed_id = params.get("openid.claimed_id", "")
    steam_id = claimed_id.rstrip("/").split("/")[-1]
    if not steam_id.isdigit():
        return login_redirect(steam_error="Steam ID was not returned")

    user = await session.scalar(select(User).where(User.steam_id == steam_id))
    if user is None:
        return login_redirect(steam_error="Steam account is not linked")
    if user.status != UserStatus.active:
        return login_redirect(steam_error=f"Account status is {user.status.value}")

    return login_redirect(token=create_access_token(user))


@router.get("/me", response_model=UserPrivate)
async def me(user: User = Depends(get_current_user)):
    return user
