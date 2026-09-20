from app.core.config import Settings
from app.core.llm import LLMFactory, MockChatModel


def test_llm_factory_mock():
    factory = LLMFactory(Settings(llm_provider="mock", llm_model="qwen3-32b"))
    model = factory.get()
    assert isinstance(model, MockChatModel)


def test_llm_factory_dashscope_requires_key():
    factory = LLMFactory(
        Settings(llm_provider="dashscope", dashscope_api_key="", llm_model="qwen3-32b")
    )
    try:
        factory.get()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "DASHSCOPE_API_KEY" in str(exc)


def test_llm_factory_openai_compatible_builds():
    factory = LLMFactory(
        Settings(
            llm_provider="openai_compatible",
            openai_api_key="sk-test",
            openai_base_url="http://localhost:9999/v1",
            llm_model="qwen3-32b",
        )
    )
    model = factory.get()
    assert model is not None


def test_llm_factory_hospital_builds():
    factory = LLMFactory(
        Settings(
            llm_provider="hospital",
            hospital_llm_base_url=(
                "http://172.28.24.104:30020/endpoint/AFTYb_g8w89_28ZWS/v1"
            ),
            hospital_llm_api_key="0fdc3ad71bfb5a97989a2efdf959d7e7",
            hospital_llm_model="Qwen3-32B",
        )
    )
    model = factory.get()
    assert model is not None
    assert model.model_name == "Qwen3-32B"
    headers = getattr(model, "default_headers", None) or {}
    assert headers.get("X-API-KEY") == "0fdc3ad71bfb5a97989a2efdf959d7e7"


def test_llm_factory_hospital_requires_key():
    factory = LLMFactory(
        Settings(
            llm_provider="hospital",
            hospital_llm_api_key="",
            hospital_llm_base_url="http://172.28.24.104:30020/endpoint/x/v1",
        )
    )
    try:
        factory.get()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "HOSPITAL_LLM_API_KEY" in str(exc)
