from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
    }
)


def _host_is_blocked_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _resolve_host_ips(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return []
    ips: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            ips.append(sockaddr[0])
    return ips


def validate_target_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Разрешены только URL с http или https")
    if not parsed.netloc:
        raise ValueError("Некорректный URL")
    if parsed.username or parsed.password:
        raise ValueError("URL не должен содержать логин или пароль")

    host = parsed.hostname
    if not host:
        raise ValueError("Некорректный URL")

    lower = host.lower()
    if lower in _BLOCKED_HOSTS or lower.endswith(".local"):
        raise ValueError("Этот адрес проверять нельзя")

    if _host_is_blocked_ip(host):
        raise ValueError("Этот адрес проверять нельзя")

    for ip in _resolve_host_ips(host):
        if _host_is_blocked_ip(ip):
            raise ValueError("Этот адрес проверять нельзя")

    return url.strip()