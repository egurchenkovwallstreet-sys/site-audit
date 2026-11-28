from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Cookie, HTTPException, Response

from app.config import get_settings

COOKIE_NAME = "site_audit_admin"


def _sign_token(email: str, *, secret: str, ttl_sec: int) -> str:
    exp = int(time.time()) + ttl_sec
    payload = f"{email.lower().strip()}:{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def _verify_token(token: str, *, secret: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        payload, sig = raw.rsplit("|", 1)
        email, exp_s = payload.rsplit(":", 1)
        exp = int(exp_s)
    except (ValueError, UnicodeDecodeError):
        return None
    if exp < time.time():
        return None
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return email


def admin_configured() -> bool:
    s = get_settings()
    return bool(s.admin_email and s.admin_password and s.admin_session_secret)


def issue_admin_session(response: Response, email: str) -> None:
    settings = get_settings()
    token = _sign_token(
        email,
        secret=settings.admin_session_secret,
        ttl_sec=settings.admin_session_ttl_sec,
    )
    secure = settings.app_env == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.admin_session_ttl_sec,
        path="/",
    )


def clear_admin_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def verify_login(email: str, password: str) -> bool:
    settings = get_settings()
    if not admin_configured():
        return False
    if email.strip().lower() != settings.admin_email.strip().lower():
        return False
    return secrets.compare_digest(password, settings.admin_password)


def require_admin(
    site_audit_admin: str | None = Cookie(default=None),
) -> str:
    if not admin_configured():
        raise HTTPException(
            status_code=503,
            detail="Админ-кабинет не настроен на сервере.",
        )
    settings = get_settings()
    if not site_audit_admin:
        raise HTTPException(status_code=401, detail="Требуется вход")
    email = _verify_token(
        site_audit_admin,
        secret=settings.admin_session_secret,
    )
    if email is None:
        raise HTTPException(status_code=401, detail="Сессия истекла")
    return email