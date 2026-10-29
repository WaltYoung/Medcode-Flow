from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import Field

from app.core.config import Settings, get_settings


class MockChatModel(BaseChatModel):
    """Deterministic LLM for topology tests and local smoke runs."""

    model_name: str = Field(default="mock")
    responses: dict[str, str] = Field(default_factory=dict)

    @property
    def _llm_type(self) -> str:
        return "mock-chat"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        joined = "\n".join(str(m.content) for m in messages)
        content = "[mock] ok"
        for key, value in self.responses.items():
            if key in joined:
                content = value
                break
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


_MISSING_MODEL = "未配置模型，已停止。请先在大模型配置里填写并保存模型 Key。"


def llm_configuration_error(settings: Settings | None = None) -> str | None:
    """没有可用模型时返回原因。测试可设置 LLM_ALLOW_MOCK=1 继续使用占位模型。"""
    settings = settings or get_settings()
    provider = settings.llm_provider
    if provider == "mock":
        allow = os.getenv("LLM_ALLOW_MOCK", "").strip().lower()
        if allow in {"1", "true", "yes"}:
            return None
        return _MISSING_MODEL
    if provider == "dashscope" and not settings.dashscope_api_key.strip():
        return _MISSING_MODEL
    if provider == "openai_compatible" and not settings.openai_api_key.strip():
        return _MISSING_MODEL
    if provider == "hospital" and not settings.hospital_llm_api_key.strip():
        return _MISSING_MODEL
    return None


class LLMFactory:
    """Unified factory: dashscope | openai_compatible | hospital | mock."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get(
        self,
        *,
        model: str | None = None,
        temperature: float | None = None,
        mock_responses: dict[str, str] | None = None,
    ) -> BaseChatModel:
        provider = self.settings.llm_provider
        temp = (
            self.settings.llm_temperature
            if temperature is None
            else temperature
        )
        timeout = self.settings.llm_timeout_seconds

        if provider == "mock":
            missing = llm_configuration_error(self.settings)
            if missing:
                raise ValueError(missing)
            return MockChatModel(
                model_name=model or self.settings.llm_model,
                responses=mock_responses or {},
            )

        if provider == "dashscope":
            if not self.settings.dashscope_api_key:
                raise ValueError("DASHSCOPE_API_KEY is required for dashscope provider")
            return ChatOpenAI(
                model=model or self.settings.llm_model,
                temperature=temp,
                api_key=self.settings.dashscope_api_key,
                base_url=self.settings.dashscope_base_url,
                timeout=timeout,
                max_retries=1,
            )

        if provider == "openai_compatible":
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for openai_compatible provider")
            return ChatOpenAI(
                model=model or self.settings.llm_model,
                temperature=temp,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                timeout=timeout,
                max_retries=1,
            )

        if provider == "hospital":
            if not self.settings.hospital_llm_api_key:
                raise ValueError(
                    "HOSPITAL_LLM_API_KEY is required for hospital provider"
                )
            if not self.settings.hospital_llm_base_url:
                raise ValueError(
                    "HOSPITAL_LLM_BASE_URL is required for hospital provider"
                )
            # 医院网关使用 X-API-KEY，而非 Authorization: Bearer
            model_name = model or self.settings.hospital_llm_model or self.settings.llm_model
            return ChatOpenAI(
                model=model_name,
                temperature=temp,
                api_key="unused",
                base_url=self.settings.hospital_llm_base_url.rstrip("/"),
                timeout=timeout,
                max_retries=1,
                default_headers={
                    "X-API-KEY": self.settings.hospital_llm_api_key,
                },
            )

        raise ValueError(f"Unsupported LLM provider: {provider}")


_factory: LLMFactory | None = None


def get_llm_factory() -> LLMFactory:
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory
