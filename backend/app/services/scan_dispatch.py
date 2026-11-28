from __future__ import annotations

import asyncio
import logging

from app.services.scan_queue import decrement_slot, fill_scan_slots, set_slots_in_use

logger = logging.getLogger(__name__)


async def run_scan_with_slot(scan_id: int, run_fn) -> None:
    """run_fn — async callable(scan_id), например _run_scan_task."""
    try:
        await run_fn(scan_id)
    except Exception:
        logger.exception("scan worker failed scan_id=%s", scan_id)
    finally:
        await decrement_slot()
        await fill_scan_slots(run_fn)


def launch_scan_worker(scan_id: int, run_fn) -> None:
    asyncio.create_task(run_scan_with_slot(scan_id, run_fn))


async def bootstrap_queue_after_startup(run_scan_task) -> None:
    """Слотов в памяти нет — running уже сброшены в queued до вызова."""
    set_slots_in_use(0)
    await fill_scan_slots(run_scan_task)