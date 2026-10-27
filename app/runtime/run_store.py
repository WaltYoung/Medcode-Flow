"""一次工作流运行和每个节点的输入输出。"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_LOCK = threading.Lock()
_CONN: sqlite3.Connection | None = None
_MAX_TEXT = 20000


def _db_path() -> Path:
    settings = get_settings()
    raw = (settings.workflow_log_path or "").strip()
    root = Path(__file__).resolve().parents[2]
    path = Path(raw) if raw else root / "data" / "workflow_runs.sqlite"
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(str(_db_path()), check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_run (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                workflow_id TEXT,
                user_id TEXT,
                status TEXT,
                inputs_json TEXT,
                outputs_json TEXT,
                error TEXT,
                total_steps INTEGER,
                elapsed_time REAL,
                created_at INTEGER,
                finished_at INTEGER
            )
            """
        )
        _CONN.execute(
            """
            CREATE TABLE IF NOT EXISTS node_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_run_id TEXT,
                node_id TEXT,
                title TEXT,
                index_no INTEGER,
                status TEXT,
                inputs_json TEXT,
                outputs_json TEXT,
                error TEXT,
                elapsed_time REAL,
                created_at INTEGER
            )
            """
        )
        _CONN.commit()
    return _CONN


def _shrink(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > _MAX_TEXT:
            return value[:_MAX_TEXT] + "…(已截断)"
        return value
    if isinstance(value, dict):
        return {str(k): _shrink(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shrink(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    text = str(value)
    if len(text) > _MAX_TEXT:
        return text[:_MAX_TEXT] + "…(已截断)"
    return text


def _dumps(value: Any) -> str:
    return json.dumps(_shrink(value), ensure_ascii=False, default=str)


def _loads(raw: str | None) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def create_run(
    *,
    run_id: str,
    task_id: str,
    workflow_id: str,
    user_id: str,
    inputs: dict[str, Any],
) -> int:
    now = int(time.time())
    with _LOCK:
        _conn().execute(
            """
            INSERT INTO workflow_run (
                id, task_id, workflow_id, user_id, status, inputs_json,
                outputs_json, error, total_steps, elapsed_time, created_at, finished_at
            ) VALUES (?, ?, ?, ?, 'running', ?, '{}', NULL, 0, 0, ?, NULL)
            """,
            (run_id, task_id, workflow_id, user_id, _dumps(inputs), now),
        )
        _conn().commit()
    return now


def append_node(
    *,
    run_id: str,
    node_id: str,
    title: str,
    index_no: int,
    status: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    elapsed_time: float,
    error: str | None = None,
) -> dict[str, Any]:
    row = {
        "node_id": node_id,
        "title": title,
        "index": index_no,
        "status": status,
        "elapsed_time": elapsed_time,
        "error": error,
        "inputs": _shrink(inputs),
        "outputs": _shrink(outputs),
    }
    with _LOCK:
        _conn().execute(
            """
            INSERT INTO node_execution (
                workflow_run_id, node_id, title, index_no, status,
                inputs_json, outputs_json, error, elapsed_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                node_id,
                title,
                index_no,
                status,
                _dumps(inputs),
                _dumps(outputs),
                error,
                elapsed_time,
                int(time.time()),
            ),
        )
        _conn().commit()
    return row


def finish_run(
    *,
    run_id: str,
    status: str,
    outputs: dict[str, Any],
    total_steps: int,
    elapsed_time: float,
    error: str | None = None,
) -> None:
    with _LOCK:
        _conn().execute(
            """
            UPDATE workflow_run
            SET status = ?, outputs_json = ?, error = ?, total_steps = ?,
                elapsed_time = ?, finished_at = ?
            WHERE id = ?
            """,
            (status, _dumps(outputs), error, total_steps, elapsed_time, int(time.time()), run_id),
        )
        _conn().commit()


def get_run(run_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _conn().execute("SELECT * FROM workflow_run WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        nodes = _conn().execute(
            "SELECT * FROM node_execution WHERE workflow_run_id = ? ORDER BY index_no, id",
            (run_id,),
        ).fetchall()
    tracing = [
        {
            "node_id": node["node_id"],
            "title": node["title"],
            "index": node["index_no"],
            "status": node["status"],
            "elapsed_time": node["elapsed_time"],
            "error": node["error"],
            "inputs": _loads(node["inputs_json"]),
            "outputs": _loads(node["outputs_json"]),
        }
        for node in nodes
    ]
    return {
        "id": row["id"],
        "workflow_run_id": row["id"],
        "task_id": row["task_id"],
        "workflow_id": row["workflow_id"],
        "status": row["status"],
        "inputs": _loads(row["inputs_json"]),
        "outputs": _loads(row["outputs_json"]),
        "error": row["error"],
        "total_steps": row["total_steps"] or 0,
        "total_tokens": 0,
        "elapsed_time": row["elapsed_time"] or 0,
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
        "tracing": tracing,
        "user": row["user_id"],
    }
