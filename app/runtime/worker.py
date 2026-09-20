from __future__ import annotations

import logging
import time

import httpx

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.runtime.executor import executor
from app.runtime.tasks import TaskStatus, task_store
from app.runtime.bootstrap import discover_workflows

logger = logging.getLogger(__name__)


def _maybe_callback(callback_url: str | None, body: dict) -> None:
    if not callback_url:
        return
    try:
        httpx.post(callback_url, json=body, timeout=10.0)
    except Exception:
        logger.exception("callback_failed url=%s", callback_url)


def process_one(task_id: str) -> None:
    record = task_store.get(task_id)
    if record is None:
        logger.warning("task_missing task_id=%s", task_id)
        return
    task_store.update(task_id, status=TaskStatus.running.value)
    try:
        result = executor.invoke(
            record["workflow_id"],
            record["payload"],
            trace_id=task_id,
        )
        updated = task_store.update(
            task_id,
            status=TaskStatus.succeeded.value,
            result=result,
            error=None,
        )
        _maybe_callback(record.get("callback_url"), updated)
    except Exception as exc:
        logger.exception("task_failed task_id=%s", task_id)
        updated = task_store.update(
            task_id,
            status=TaskStatus.failed.value,
            error={"message": str(exc), "error_code": "WORKFLOW_FAILED"},
        )
        _maybe_callback(record.get("callback_url"), updated)


def run_forever() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    discover_workflows()
    logger.info("worker_started redis=%s", settings.redis_url)
    while True:
        task_id = task_store.pop_next(timeout=2)
        if task_id:
            process_one(task_id)
        else:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    run_forever()
