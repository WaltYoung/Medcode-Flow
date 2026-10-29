from fastapi import APIRouter

from app.api.v1 import health, runtime_llm, workflows

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(workflows.router)
api_router.include_router(workflows.tasks_router)
api_router.include_router(runtime_llm.router)
