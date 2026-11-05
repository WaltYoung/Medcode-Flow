from app.api.v1.runtime_llm import _looks_like_hospital_gateway, _resolve_provider


def test_resolve_custom_to_hospital():
    assert _resolve_provider("custom") == "hospital"
    assert _resolve_provider("hospital") == "hospital"


def test_resolve_openai_compatible_default():
    assert _resolve_provider("openai_compatible") == "openai_compatible"
    assert _resolve_provider("qwen") == "openai_compatible"


def test_url_forces_hospital_even_if_provider_wrong():
    url = "http://172.28.24.104:30020/endpoint/AFTYb_g8w89_28ZWS/v1"
    assert _looks_like_hospital_gateway(url) is True
    assert _resolve_provider("openai_compatible", url) == "hospital"
    assert _resolve_provider("qwen", url) == "hospital"
