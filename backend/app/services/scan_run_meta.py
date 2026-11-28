from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.models.entities import Scan


RUN_META_KEY = "_run"


def read_context(scan: Scan) -> dict[str, Any]:
    if not scan.context_json:
        return {}
    try:
        raw = json.loads(scan.context_json)
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def read_run_meta(scan: Scan) -> dict[str, Any]:
    ctx = read_context(scan)
    meta = ctx.get(RUN_META_KEY)
    if not isinstance(meta, dict):
        meta = {}
    phase = int(meta.get("phase") or 1)
    if phase < 1:
        phase = 1
    if phase > 2:
        phase = 2
    return {
        "phase": phase,
        "auto_retries": int(meta.get("auto_retries") or 0),
        "extension_used": bool(meta.get("extension_used")) or phase >= 2,
    }


def merge_context(scan: Scan, patch: dict[str, Any]) -> dict[str, Any]:
    ctx = read_context(scan)
    ctx.update(patch)
    return ctx


def write_context(scan: Scan, ctx: dict[str, Any]) -> None:
    scan.context_json = json.dumps(ctx, ensure_ascii=False)


def effective_time_budget_sec(scan: Scan) -> float:
    settings = get_settings()
    meta = read_run_meta(scan)
    if meta["phase"] >= 2 or meta["extension_used"]:
        return float(settings.scan_time_budget_sec + settings.scan_time_extension_sec)
    return float(settings.scan_time_budget_sec)


def task_timeout_for_scan(scan: Scan) -> float:
    settings = get_settings()
    meta = read_run_meta(scan)
    buf = float(settings.scan_task_timeout_buffer_sec)
    if meta["phase"] >= 2:
        total = settings.scan_time_budget_sec + settings.scan_time_extension_sec
        return float(total) + buf
    return float(settings.scan_time_budget_sec) + buf


def init_run_meta_on_start(scan: Scan) -> None:
    ctx = read_context(scan)
    meta = ctx.get(RUN_META_KEY)
    if not isinstance(meta, dict):
        meta = {}
    if not meta.get("started_at"):
        meta["started_at"] = datetime.now(timezone.utc).isoformat()
    meta.setdefault("phase", 1)
    meta.setdefault("auto_retries", 0)
    ctx[RUN_META_KEY] = meta
    write_context(scan, ctx)


def bump_to_phase2(scan: Scan) -> None:
    ctx = read_context(scan)
    meta = ctx.get(RUN_META_KEY)
    if not isinstance(meta, dict):
        meta = {}
    meta["phase"] = 2
    meta["extension_used"] = True
    meta["extended_at"] = datetime.now(timezone.utc).isoformat()
    ctx[RUN_META_KEY] = meta
    ctx["scan_phase_note"] = (
        "Добавлено ещё 10 минут: первая фаза не уложилась в лимит."
    )
    write_context(scan, ctx)


def bump_auto_retry(scan: Scan) -> int:
    ctx = read_context(scan)
    meta = ctx.get(RUN_META_KEY)
    if not isinstance(meta, dict):
        meta = {}
    n = int(meta.get("auto_retries") or 0) + 1
    meta["auto_retries"] = n
    meta["last_auto_retry_at"] = datetime.now(timezone.utc).isoformat()
    ctx[RUN_META_KEY] = meta
    write_context(scan, ctx)
    return n