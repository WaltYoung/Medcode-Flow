from __future__ import annotations

from fastapi import APIRouter

from app.runtime.registry import registry

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, object]:
    return {
        "status": "ok",
        "workflows": [spec.workflow_id for spec in registry.list()],
    }
