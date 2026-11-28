from __future__ import annotations

from fastapi import Request


def client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip[:45]
    if request.client and request.client.host:
        return request.client.host[:45]
    return "unknown"