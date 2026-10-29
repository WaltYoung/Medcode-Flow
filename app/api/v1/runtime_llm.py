"""接收应用页面保存的外网模型，运行中立即生效。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.llm import get_llm_factory
from app.core.security import require_api_key

router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[Depends(require_api_key)])


class RuntimeLlmIn(BaseModel):
    base_url: str = Field(..., max_length=300)
    model: str = Field(..., max_length=128)
    api_key: str = Field(..., min_length=1)


@router.put("/llm")
async def apply_runtime_llm(body: RuntimeLlmIn) -> dict[str, str]:
    settings = get_settings()
    settings.llm_provider = "openai_compatible"
    settings.openai_base_url = body.base_url.strip().rstrip("/")
    settings.openai_api_key = body.api_key.strip()
    settings.llm_model = body.model.strip()
    get_llm_factory().settings = settings
    return {"status": "ok", "model": settings.llm_model}
