from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "langgraph-workflows"
    app_env: str = "dev"
    api_key: str = "change-me-in-production"
    log_level: str = "INFO"

    llm_provider: Literal[
        "dashscope",
        "openai_compatible",
        "hospital",
        "mock",
    ] = "mock"
    llm_model: str = "qwen3-32b"
    llm_temperature: float = 0.1
    llm_timeout_seconds: int = 120

    dashscope_api_key: str = ""
    dashscope_base_url: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    openai_api_key: str = ""
    openai_base_url: str = "http://localhost:8000/v1"

    # 医院内部算力（OpenAI 兼容 /chat/completions，鉴权头为 X-API-KEY）
    hospital_llm_base_url: str = (
        "http://172.28.24.104:30020/endpoint/AFTYb_g8w89_28ZWS/v1"
    )
    hospital_llm_api_key: str = "0fdc3ad71bfb5a97989a2efdf959d7e7"
    hospital_llm_model: str = "Qwen3-32B"

    redis_url: str = "redis://localhost:6379/0"
    task_ttl_seconds: int = 86400
    workflow_timeout_seconds: int = 600
    worker_poll_interval_seconds: float = 1.0

    # 智能病案编码检索服务（文档默认 8000，本环境实际 8090）
    kb_base_url: str = "http://127.0.0.1:8090"
    kb_top_k: int = 4
    kb_candidate_k: int = 80
    kb_timeout_seconds: float = 30.0
    kb_enabled: bool = True

    log_redact_input: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
