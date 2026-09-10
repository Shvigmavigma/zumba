from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from fastapi import Request, Response

from app.config import get_settings


DEVICE_COOKIE_NAME = "bmrl_device"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 730


def device_token_for_request(request: Request) -> tuple[str, bool]:
    token = (request.cookies.get(DEVICE_COOKIE_NAME) or "").strip()
    if 32 <= len(token) <= 200:
        return token, False
    return secrets.token_urlsafe(32), True


def set_device_cookie(response: Response, token: str, request: Request) -> None:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        token,
        max_age=DEVICE_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https" or forwarded_proto == "https",
        samesite="lax",
        path="/",
    )


def fingerprint_device_token(token: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def describe_user_agent(user_agent: str | None) -> str:
    value = (user_agent or "").strip()
    if not value:
        return "Unknown device"

    if re.search(r"iPad", value, re.IGNORECASE):
        platform = "iPad"
    elif re.search(r"iPhone", value, re.IGNORECASE):
        platform = "iPhone"
    elif re.search(r"Android", value, re.IGNORECASE):
        platform = "Android"
    elif re.search(r"Windows Phone", value, re.IGNORECASE):
        platform = "Windows Phone"
    elif re.search(r"Windows NT", value, re.IGNORECASE):
        platform = "Windows"
    elif re.search(r"Mac OS X", value, re.IGNORECASE):
        platform = "macOS"
    elif re.search(r"Linux", value, re.IGNORECASE):
        platform = "Linux"
    else:
        platform = "Unknown platform"

    if re.search(r"Edg(?:e|A|iOS)?/", value, re.IGNORECASE):
        browser = "Edge"
    elif re.search(r"OPR/|Opera", value, re.IGNORECASE):
        browser = "Opera"
    elif re.search(r"YaBrowser/", value, re.IGNORECASE):
        browser = "Yandex Browser"
    elif re.search(r"SamsungBrowser/", value, re.IGNORECASE):
        browser = "Samsung Internet"
    elif re.search(r"Firefox/|FxiOS/", value, re.IGNORECASE):
        browser = "Firefox"
    elif re.search(r"Chrome/|CriOS/", value, re.IGNORECASE):
        browser = "Chrome"
    elif re.search(r"Safari/", value, re.IGNORECASE):
        browser = "Safari"
    else:
        browser = "Unknown browser"

    return f"{platform} · {browser}"
