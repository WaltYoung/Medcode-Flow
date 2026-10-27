"""应用编码正在调用的两个工作流接口。"""

from __future__ import annotations

import json
import queue
import threading
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.runtime.bootstrap import discover_workflows
from app.runtime.registry import registry
from app.runtime.run_store import get_run
from app.runtime.traced_run import RunOutcome, run_workflow

router = APIRouter(tags=["workflow-compat"])


class WorkflowRunIn(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    response_mode: str = "blocking"
    user: str = ""
    trace_id: str | None = None


def _key_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    raw = get_settings().workflow_key_map or ""
    for part in raw.split(","):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, workflow_id = item.split("=", 1)
        key = key.strip()
        workflow_id = workflow_id.strip()
        if key and workflow_id:
            mapping[key] = workflow_id
    return mapping


def _bearer(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authorization 需要 Bearer Key")
    return token.strip()


def resolve_workflow_id(authorization: str | None, x_workflow_id: str | None) -> str:
    discover_workflows()
    token = _bearer(authorization)
    mapped = _key_map().get(token)
    if mapped:
        workflow_id = mapped
    elif token == get_settings().api_key:
        workflow_id = (x_workflow_id or "").strip()
        if not workflow_id:
            raise HTTPException(status_code=400, detail="使用总 Key 时需要请求头 X-Workflow-Id")
    else:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    if workflow_id not in registry:
        raise HTTPException(status_code=400, detail=f"未登记的工作流: {workflow_id}")
    return workflow_id


def _data_block(outcome: RunOutcome) -> dict[str, Any]:
    return {
        "id": outcome.run_id,
        "workflow_id": outcome.workflow_id,
        "status": outcome.status,
        "outputs": outcome.outputs,
        "error": outcome.error,
        "elapsed_time": outcome.elapsed_time,
        "total_tokens": 0,
        "total_steps": outcome.total_steps,
        "created_at": outcome.created_at,
        "finished_at": outcome.finished_at,
        "tracing": outcome.tracing,
    }


def _blocking_body(outcome: RunOutcome) -> dict[str, Any]:
    return {
        "workflow_run_id": outcome.run_id,
        "task_id": outcome.task_id,
        "data": _data_block(outcome),
    }


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _finished_payload(outcome: RunOutcome) -> dict[str, Any]:
    return {
        "workflow_run_id": outcome.run_id,
        "task_id": outcome.task_id,
        "status": outcome.status,
        "outputs": outcome.outputs,
        "error": outcome.error,
        "elapsed_time": outcome.elapsed_time,
        "total_tokens": 0,
        "total_steps": outcome.total_steps,
        "tracing": outcome.tracing,
    }


def _execute(workflow_id: str, body: WorkflowRunIn, on_event=None) -> RunOutcome:
    spec = registry.get(workflow_id)
    try:
        spec.request_model.model_validate(body.inputs)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    return run_workflow(
        spec,
        body.inputs,
        user_id=body.user,
        trace_id=body.trace_id,
        on_event=on_event,
    )


def _stream(workflow_id: str, body: WorkflowRunIn):
    events: queue.Queue[str | None] = queue.Queue()
    holder: dict[str, RunOutcome] = {}

    def on_event(event: str, payload: dict[str, Any]) -> None:
        events.put(_sse(event, payload))

    def worker() -> None:
        try:
            holder["outcome"] = _execute(workflow_id, body, on_event=on_event)
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = events.get()
        if item is None:
            break
        yield item
    outcome = holder.get("outcome")
    if outcome is not None:
        yield _sse("workflow_finished", _finished_payload(outcome))


@router.post("/workflows/run")
def run_published_workflow(
    body: WorkflowRunIn,
    authorization: str | None = Header(default=None),
    x_workflow_id: str | None = Header(default=None),
):
    workflow_id = resolve_workflow_id(authorization, x_workflow_id)
    if body.response_mode not in {"blocking", "streaming"}:
        raise HTTPException(status_code=400, detail="response_mode 只能是 blocking 或 streaming")
    if body.response_mode == "streaming":
        spec = registry.get(workflow_id)
        try:
            spec.request_model.model_validate(body.inputs)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=exc.errors()) from exc
        return StreamingResponse(
            _stream(workflow_id, body),
            media_type="text/event-stream",
        )
    return _blocking_body(_execute(workflow_id, body))


@router.get("/workflows/run/{workflow_run_id}")
def get_published_run(
    workflow_run_id: str,
    authorization: str | None = Header(default=None),
    x_workflow_id: str | None = Header(default=None),
):
    resolve_workflow_id(authorization, x_workflow_id)
    row = get_run(workflow_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow 执行记录不存在")
    return row
