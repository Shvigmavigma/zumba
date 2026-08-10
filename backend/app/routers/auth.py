from urllib.parse import urlencode

import httpx
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import clear_expired_timeout, get_current_user
from app.models import DEFAULT_SR, Role, Team, User, UserStatus
from app.rate_limit import limiter
from app.schemas import LoginRequest, TokenResponse, UserPrivate, UserRegister
from app.security import (
    create_access_token,
    create_steam_registration_token,
    decode_steam_registration_token,
    hash_password,
    verify_password,
)


router = APIRouter()
settings = get_settings()


async def private_user_response(session: AsyncSession, user: User) -> UserPrivate:
    team = await session.get(Team, user.team_id) if user.team_id is not None else None
    data = UserPrivate.model_validate(user).model_dump()
    data["team_name"] = team.name if team else None
    data["team_abbreviation"] = team.abbreviation if team else None
    return UserPrivate(**data)


def login_redirect(**params: str) -> RedirectResponse:
    query = urlencode(params)
    return RedirectResponse(f"{settings.public_base_url.rstrip('/')}/login?{query}", status_code=302)


def register_redirect(**params: str) -> RedirectResponse:
    query = urlencode(params)
    return RedirectResponse(f"{settings.public_base_url.rstrip('/')}/register?{query}", status_code=302)


def steam_flow_redirect(flow: str, **params: str) -> RedirectResponse:
    if flow == "register":
        return register_redirect(**params)
    return login_redirect(**params)


def is_loopback_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


@router.post("/register", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(payload: UserRegister, request: Request, session: AsyncSession = Depends(get_session)):
    steam_id = decode_steam_registration_token(payload.steam_auth_token)
    duplicate = await session.scalar(
        select(User).where(
            or_(
                User.login == payload.login,
                User.email == payload.email,
                User.pilot_number == payload.pilot_number,
                User.steam_id == steam_id,
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
        sr=DEFAULT_SR,
        discord=payload.discord,
        steam_id=steam_id,
        role=Role.pilot,
        status=UserStatus.unapproved,
        avatar_color=payload.avatar_color,
        games=payload.games,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return await private_user_response(session, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(or_(User.login == payload.login, User.email == payload.login)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if clear_expired_timeout(user):
        await session.commit()
        await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=await private_user_response(session, user))


@router.get("/steam/start")
@limiter.limit("20/minute")
async def steam_start(request: Request, flow: str = "login"):
    if flow not in {"login", "register"}:
        raise HTTPException(status_code=400, detail="Unsupported Steam auth flow")
    base_url = settings.public_base_url.rstrip("/")
    if is_loopback_url(base_url):
        return steam_flow_redirect(
            flow,
            steam_error="Steam blocks localhost callbacks. Set PUBLIC_BASE_URL to a public HTTPS URL and restart Docker.",
        )
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{base_url}/api/auth/steam/callback/{flow}",
        "openid.realm": base_url,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return RedirectResponse(f"{settings.steam_openid_url}?{urlencode(params)}", status_code=302)


async def finish_steam_callback(request: Request, flow: str, session: AsyncSession):
    if flow not in {"login", "register"}:
        return login_redirect(steam_error="Unsupported Steam authentication flow")
    params = dict(request.query_params)
    if params.get("openid.mode") != "id_res":
        if flow == "register":
            return register_redirect(steam_error="Steam authentication was cancelled")
        return login_redirect(steam_error="Steam authentication was cancelled")

    verify_payload = {key: value for key, value in params.items() if key.startswith("openid.")}
    verify_payload["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(settings.steam_openid_url, data=verify_payload)
    if "is_valid:true" not in response.text:
        if flow == "register":
            return register_redirect(steam_error="Steam authentication failed")
        return login_redirect(steam_error="Steam authentication failed")

    claimed_id = params.get("openid.claimed_id", "")
    steam_id = claimed_id.rstrip("/").split("/")[-1]
    if not steam_id.isdigit():
        if flow == "register":
            return register_redirect(steam_error="Steam ID was not returned")
        return login_redirect(steam_error="Steam ID was not returned")

    user = await session.scalar(select(User).where(User.steam_id == steam_id))
    if flow == "register":
        if user is not None:
            return register_redirect(steam_error="Steam account is already linked")
        return register_redirect(steam_id=steam_id, steam_auth_token=create_steam_registration_token(steam_id))

    if user is None:
        return login_redirect(steam_error="Steam account is not linked")
    if clear_expired_timeout(user):
        await session.commit()
        await session.refresh(user)
    if user.status != UserStatus.active:
        return login_redirect(steam_error=f"Account status is {user.status.value}")

    return login_redirect(token=create_access_token(user))


@router.get("/steam/callback/{flow}")
@limiter.limit("20/minute")
async def steam_callback_for_flow(flow: str, request: Request, session: AsyncSession = Depends(get_session)):
    return await finish_steam_callback(request, flow, session)


@router.get("/steam/callback")
@limiter.limit("20/minute")
async def steam_callback(request: Request, flow: str = "login", session: AsyncSession = Depends(get_session)):
    return await finish_steam_callback(request, flow, session)


@router.get("/me", response_model=UserPrivate)
async def me(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await private_user_response(session, user)
