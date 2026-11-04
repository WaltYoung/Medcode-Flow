"""接收应用页面保存的外网模型，运行中立即生效。"""

from __future__ import annotations

from typing import Literal

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
    # hospital/custom：院内网关用 X-API-KEY；其余走 Bearer（openai_compatible）
    provider: str = Field(default="openai_compatible", max_length=32)


def _resolve_provider(raw: str) -> Literal["hospital", "openai_compatible"]:
    name = (raw or "").strip().lower()
    if name in {"hospital", "custom", "x_api_key", "x-api-key"}:
        return "hospital"
    return "openai_compatible"


@router.put("/llm")
async def apply_runtime_llm(body: RuntimeLlmIn) -> dict[str, str]:
    settings = get_settings()
    base = body.base_url.strip().rstrip("/")
    model = body.model.strip()
    key = body.api_key.strip()
    provider = _resolve_provider(body.provider)
    settings.llm_model = model
    if provider == "hospital":
        # 医院网关拒绝 Authorization: Bearer，必须走 X-API-KEY
        settings.llm_provider = "hospital"
        settings.hospital_llm_base_url = base
        settings.hospital_llm_api_key = key
        settings.hospital_llm_model = model
    else:
        settings.llm_provider = "openai_compatible"
        settings.openai_base_url = base
        settings.openai_api_key = key
    get_llm_factory().settings = settings
    return {"status": "ok", "model": settings.llm_model, "provider": settings.llm_provider}
