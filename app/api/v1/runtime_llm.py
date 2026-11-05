"""接收应用页面保存的外网模型，运行中立即生效。"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

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


def _looks_like_hospital_gateway(base_url: str) -> bool:
    """院内网关路径/内网段：即使 provider 填错也强制 X-API-KEY，避免 400 凭证缺失。"""
    raw = (base_url or "").strip().lower()
    if not raw:
        return False
    if "/endpoint/" in raw:
        return True
    host = (urlparse(raw).hostname or "").lower()
    if host.startswith("172.28.24."):
        return True
    configured = (get_settings().hospital_llm_base_url or "").strip().lower()
    cfg_host = (urlparse(configured).hostname or "").lower()
    return bool(cfg_host and host == cfg_host)


def _resolve_provider(
    raw: str, base_url: str = ""
) -> Literal["hospital", "openai_compatible"]:
    name = (raw or "").strip().lower()
    if name in {"hospital", "custom", "x_api_key", "x-api-key"}:
        return "hospital"
    if _looks_like_hospital_gateway(base_url):
        return "hospital"
    return "openai_compatible"


@router.put("/llm")
async def apply_runtime_llm(body: RuntimeLlmIn) -> dict[str, str]:
    settings = get_settings()
    base = body.base_url.strip().rstrip("/")
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
