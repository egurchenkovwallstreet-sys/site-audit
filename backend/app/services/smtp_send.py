from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings


class SmtpNotConfiguredError(RuntimeError):
    pass


class SmtpDeliveryError(RuntimeError):
    pass


def smtp_is_configured() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.smtp_user and s.smtp_password)


def _send_sync(message: EmailMessage) -> None:
    settings = get_settings()
    if not smtp_is_configured():
        raise SmtpNotConfiguredError(
            "SMTP не настроен: задайте SMTP_HOST, SMTP_USER, SMTP_PASSWORD в .env"
        )

    from_addr = settings.smtp_from or settings.smtp_user
    if "From" not in message:
        message["From"] = from_addr

    context = ssl.create_default_context()
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=45, context=context
            ) as smtp:
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=45) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=context)
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise SmtpDeliveryError(str(exc)) from exc


async def send_email_message(message: EmailMessage) -> None:
    await asyncio.to_thread(_send_sync, message)