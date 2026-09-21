from app.core.config import Settings
from app.shared.kb.client import (
    KnowledgeBaseClient,
    other_diagnosis_results_to_knowledges,
    search_results_to_knowledges,
)


def test_search_results_to_knowledges():
    rows = [
        {
            "diag_code": "K29.500",
            "diag_name": "慢性胃炎",
            "evidence": "胃炎",
            "matched_keywords": [{"kw_text": "慢性胃炎", "kw_type": "name"}],
        }
    ]
    knowledges = search_results_to_knowledges(rows)
    assert knowledges
    assert "慢性胃炎(K29.500)" in knowledges[0]["content"]


def test_other_diagnosis_results_to_knowledges():
    rows = [
        {
            "original_content": "慢性胃炎(K29.500)",
            "score": 0.91,
            "matched_keywords": [{"kw_text": "慢性胃炎", "score": 0.91}],
        }
    ]
    knowledges = other_diagnosis_results_to_knowledges(rows)
    assert knowledges == [{"content": "慢性胃炎(K29.500)"}]


def test_kb_client_search(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "query": "慢性胃炎",
                "top_k": 4,
                "results": [
                    {
                        "diag_code": "K29.500",
                        "diag_name": "慢性胃炎",
                        "score": 0.9,
                        "evidence": "慢性胃炎",
                        "matched_keywords": [],
                    }
                ],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            assert url == "http://127.0.0.1:8090/search"
            assert json["query"] == "慢性胃炎"
            assert json["top_k"] == 4
            return FakeResp()

    monkeypatch.setattr("app.shared.kb.client.httpx.Client", FakeClient)
    client = KnowledgeBaseClient(
        Settings(
            kb_base_url="http://127.0.0.1:8090",
            kb_top_k=4,
            kb_enabled=True,
        )
    )
    results = client.search("慢性胃炎")
    assert results[0]["diag_code"] == "K29.500"


def test_kb_client_search_other_diagnosis(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "query": "霍乱",
                "top_k": 4,
                "results": [
                    {
                        "original_content": "霍乱(A00.900)",
                        "score": 0.88,
                        "matched_keywords": [{"kw_text": "霍乱", "score": 0.88}],
                    }
                ],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            assert url == "http://127.0.0.1:8090/search/other-diagnosis"
            assert json["query"] == "霍乱"
            assert json["top_k"] == 4
            return FakeResp()

    monkeypatch.setattr("app.shared.kb.client.httpx.Client", FakeClient)
    client = KnowledgeBaseClient(
        Settings(
            kb_base_url="http://127.0.0.1:8090",
            kb_top_k=4,
            kb_enabled=True,
        )
    )
    results = client.search_other_diagnosis("霍乱")
    assert results[0]["original_content"] == "霍乱(A00.900)"
