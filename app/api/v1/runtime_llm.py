"""接收应用页面保存的外网模型，运行中立即生效。"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.hospital_auth import looks_like_hospital_gateway
from app.core.llm import get_llm_factory
from app.core.security import require_api_key

router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[Depends(require_api_key)])


class RuntimeLlmIn(BaseModel):
    base_url: str = Field(..., max_length=300)
    model: str = Field(..., max_length=128)
    api_key: str = Field(..., min_length=1)
    # hospital / 院内 URL → X-API-KEY；custom+公网、qwen、deepseek → Bearer
    provider: str = Field(default="openai_compatible", max_length=32)


def _resolve_provider(
    raw: str, base_url: str = ""
) -> Literal["hospital", "openai_compatible"]:
    name = (raw or "").strip().lower()
    # 显式院内；「自定义」本身不强制院内，避免外网自定义公网模型被改成 X-API-KEY
    if name in {"hospital", "x_api_key", "x-api-key"}:
        return "hospital"
    if looks_like_hospital_gateway(base_url):
        return "hospital"
    return "openai_compatible"


def _normalize_base_url(base_url: str) -> str:
    """SDK 会再拼 /chat/completions；这里去掉以免院内网关 404。"""
    url = base_url.strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if url.lower().endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
    return url


@router.put("/llm")
async def apply_runtime_llm(body: RuntimeLlmIn) -> dict[str, str]:
    settings = get_settings()
    base = _normalize_base_url(body.base_url)
    model = body.model.strip()
    key = body.api_key.strip()
    provider = _resolve_provider(body.provider, base)
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
