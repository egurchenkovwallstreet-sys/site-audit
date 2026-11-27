from __future__ import annotations

import re
import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Scan

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def new_public_token() -> str:
    return secrets.token_urlsafe(24)


def validate_public_token(token: str) -> str:
    token = token.strip()
    if not _TOKEN_RE.fullmatch(token):
        raise HTTPException(status_code=404, detail="Скан не найден")
    return token


async def scan_by_public_token(session: AsyncSession, token: str) -> Scan:
    token = validate_public_token(token)
    result = await session.execute(select(Scan).where(Scan.public_token == token))
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Скан не найден")
    return scan