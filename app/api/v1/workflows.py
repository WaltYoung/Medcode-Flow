from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.security import require_api_key
from app.runtime.executor import executor
from app.runtime.registry import registry
from app.runtime.tasks import task_store

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    dependencies=[Depends(require_api_key)],
)

tasks_router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(require_api_key)],
)


class WorkflowInfo(BaseModel):
    workflow_id: str
    name: str
    version: str
    description: str


class AsyncAccepted(BaseModel):
    task_id: str
    status: str
    workflow_id: str


class TaskView(BaseModel):
    task_id: str
    workflow_id: str
    status: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@router.get("", response_model=list[WorkflowInfo])
def list_workflows() -> list[WorkflowInfo]:
    return [
        WorkflowInfo(
            workflow_id=spec.workflow_id,
            name=spec.name,
            version=spec.version,
            description=spec.description,
        )
        for spec in registry.list()
    ]


@router.post("/{workflow_id}/invoke")
def invoke_workflow(workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_registered(workflow_id)
    try:
        return executor.invoke(workflow_id, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "WORKFLOW_FAILED", "message": str(exc)},
        ) from exc


@router.post("/{workflow_id}/invoke-async", response_model=AsyncAccepted)
def invoke_workflow_async(
    workflow_id: str,
    payload: dict[str, Any],
    callback_url: str | None = Query(default=None),
) -> AsyncAccepted:
    _ensure_registered(workflow_id)
    body_callback = payload.pop("callback_url", None)
    accepted = task_store.enqueue(
        workflow_id=workflow_id,
        payload=payload,
        callback_url=callback_url or body_callback,
    )
    return AsyncAccepted.model_validate(accepted)


@tasks_router.get("/{task_id}", response_model=TaskView)
def get_task(task_id: str) -> TaskView:
    record = task_store.get(task_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return TaskView(
        task_id=record["task_id"],
        workflow_id=record["workflow_id"],
        status=record["status"],
        result=record.get("result"),
        error=record.get("error"),
    )


def _ensure_registered(workflow_id: str) -> None:
    if workflow_id not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown workflow_id: {workflow_id}",
        )
