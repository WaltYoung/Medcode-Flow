from app.api.v1.runtime_llm import _resolve_provider
from app.core.hospital_auth import looks_like_hospital_gateway


def test_resolve_hospital_explicit():
    assert _resolve_provider("hospital") == "hospital"
    assert _resolve_provider("x-api-key") == "hospital"


def test_custom_public_stays_openai_compatible():
    """外网自定义公网模型：不能因 provider=custom 被改成 hospital。"""
    assert (
        _resolve_provider("custom", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        == "openai_compatible"
    )
    assert _resolve_provider("custom", "https://api.deepseek.com") == "openai_compatible"


def test_url_forces_hospital_even_if_provider_wrong():
    url = "http://172.28.24.104:30020/endpoint/AFTYb_g8w89_28ZWS/v1"
    assert looks_like_hospital_gateway(url) is True
    assert _resolve_provider("openai_compatible", url) == "hospital"
    assert _resolve_provider("custom", url) == "hospital"
    assert _resolve_provider("qwen", url) == "hospital"
