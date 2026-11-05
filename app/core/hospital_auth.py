"""院内算力网关鉴权：只用 X-API-KEY，禁止带上 Authorization Bearer。"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings


def looks_like_hospital_gateway(base_url: str, settings: Settings | None = None) -> bool:
    """院内网关路径/内网段判定（与页面 provider 字段无关）。"""
    raw = (base_url or "").strip().lower()
    if not raw:
        return False
    if "/endpoint/" in raw:
        return True
    host = (urlparse(raw).hostname or "").lower()
    if host.startswith("172.28.24."):
        return True
    cfg = settings or get_settings()
    configured = (cfg.hospital_llm_base_url or "").strip().lower()
    cfg_host = (urlparse(configured).hostname or "").lower()
    return bool(cfg_host and host == cfg_host)


def _strip_authorization(request: httpx.Request) -> None:
    request.headers.pop("Authorization", None)
    request.headers.pop("authorization", None)


def build_hospital_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout: float,
) -> ChatOpenAI:
    """构造只带 X-API-KEY 的 ChatOpenAI（去掉 SDK 自动加的 Bearer）。"""
    key = api_key.strip()
    base = base_url.strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
    sync_client = httpx.Client(
        timeout=timeout,
        event_hooks={"request": [_strip_authorization]},
    )
    async_client = httpx.AsyncClient(
        timeout=timeout,
        event_hooks={"request": [_strip_authorization]},
    )
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=key or "unused",
        base_url=base,
        timeout=timeout,
        max_retries=1,
        default_headers={"X-API-KEY": key},
        http_client=sync_client,
        http_async_client=async_client,
    )
