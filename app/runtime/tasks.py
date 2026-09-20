from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import deque
from enum import Enum
from typing import Any, Protocol

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "wf:tasks:queue"
TASK_KEY_PREFIX = "wf:task:"


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class TaskStoreProtocol(Protocol):
    def enqueue(
        self,
        *,
        workflow_id: str,
        payload: dict[str, Any],
        callback_url: str | None = None,
    ) -> dict[str, Any]: ...

    def get(self, task_id: str) -> dict[str, Any] | None: ...

    def update(self, task_id: str, **fields: Any) -> dict[str, Any]: ...

    def pop_next(self, timeout: int = 2) -> str | None: ...


class RedisTaskStore:
    def __init__(self, redis_url: str | None = None) -> None:
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.ttl = settings.task_ttl_seconds
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client

    def _key(self, task_id: str) -> str:
        return f"{TASK_KEY_PREFIX}{task_id}"

    def enqueue(
        self,
        *,
        workflow_id: str,
        payload: dict[str, Any],
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "task_id": task_id,
            "workflow_id": workflow_id,
            "status": TaskStatus.queued.value,
            "payload": payload,
            "callback_url": callback_url,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        pipe = self.client.pipeline()
        pipe.set(
            self._key(task_id),
            json.dumps(record, ensure_ascii=False),
            ex=self.ttl,
        )
        pipe.rpush(QUEUE_KEY, task_id)
        pipe.execute()
        return {
            "task_id": task_id,
            "status": TaskStatus.queued.value,
            "workflow_id": workflow_id,
        }

    def get(self, task_id: str) -> dict[str, Any] | None:
        raw = self.client.get(self._key(task_id))
        if not raw:
            return None
        return json.loads(raw)

    def update(self, task_id: str, **fields: Any) -> dict[str, Any]:
        record = self.get(task_id)
        if record is None:
            raise KeyError(f"task not found: {task_id}")
        record.update(fields)
        record["updated_at"] = time.time()
        self.client.set(
            self._key(task_id),
            json.dumps(record, ensure_ascii=False),
            ex=self.ttl,
        )
        return record

    def pop_next(self, timeout: int = 2) -> str | None:
        item = self.client.blpop(QUEUE_KEY, timeout=timeout)
        if not item:
            return None
        _, task_id = item
        return task_id


class MemoryTaskStore:
    """In-process store for tests and local runs without Redis."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._queue: deque[str] = deque()
        self._cv = threading.Condition()

    def enqueue(
        self,
        *,
        workflow_id: str,
        payload: dict[str, Any],
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "task_id": task_id,
            "workflow_id": workflow_id,
            "status": TaskStatus.queued.value,
            "payload": payload,
            "callback_url": callback_url,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._cv:
            self._data[task_id] = record
            self._queue.append(task_id)
            self._cv.notify()
        return {
            "task_id": task_id,
            "status": TaskStatus.queued.value,
            "workflow_id": workflow_id,
        }

    def get(self, task_id: str) -> dict[str, Any] | None:
        record = self._data.get(task_id)
        return json.loads(json.dumps(record)) if record else None

    def update(self, task_id: str, **fields: Any) -> dict[str, Any]:
        if task_id not in self._data:
            raise KeyError(f"task not found: {task_id}")
        self._data[task_id].update(fields)
        self._data[task_id]["updated_at"] = time.time()
        return self.get(task_id)  # type: ignore[return-value]

    def pop_next(self, timeout: int = 2) -> str | None:
        deadline = time.time() + timeout
        with self._cv:
            while not self._queue:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._cv.wait(timeout=remaining)
            return self._queue.popleft()


def build_task_store() -> TaskStoreProtocol:
    settings = get_settings()
    if settings.redis_url.startswith("memory://"):
        return MemoryTaskStore()
    return RedisTaskStore()


task_store: TaskStoreProtocol = build_task_store()
