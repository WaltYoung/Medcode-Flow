from app.runtime.bootstrap import discover_workflows
from app.runtime.executor import executor
from app.runtime.registry import registry
from app.workflows.other_diagnosis.graph import build_graph


class _FakeKB:
    def search_other_diagnosis(self, query: str, **kwargs):
        mapping = {
            "急性心肌梗死": "急性心肌梗死(I21.900)",
            "慢性胃炎": "慢性胃炎(K29.500)",
            "高血压病3级（极高危）": "高血压病3级（极高危）(I10.x00x032)",
        }
        content = mapping.get(query)
        if not content:
            return []
        return [
            {
                "original_content": content,
                "score": 0.9,
                "matched_keywords": [{"kw_text": query, "score": 0.9}],
            }
        ]


def test_other_diagnosis_registered():
    discover_workflows()
    assert "other_diagnosis" in registry
    assert registry.get("other_diagnosis").version == "1.0.0"


def test_other_diagnosis_graph_with_mock_kb(monkeypatch):
    monkeypatch.setattr(
        "app.workflows.other_diagnosis.nodes.workflow_nodes.get_kb_client",
        lambda: _FakeKB(),
    )
    # clear cached graph so nodes pick up monkeypatch path (nodes already imported)
    build_graph.cache_clear()
    graph = build_graph()
    state = graph.invoke(
        {
            "discharge_diagnosis": '["急性心肌梗死","高血压病3级（极高危）","慢性胃炎"]',
            "main_diagnosis": "急性心肌梗死",
        }
    )
    assert "慢性胃炎(K29.500)" in state["kb_context"]
    assert "高血压病3级（极高危）(I10.x00x032)" in state["kb_context"]
    assert state["other_diagnosis"]


def test_other_diagnosis_executor(monkeypatch):
    monkeypatch.setattr(
        "app.workflows.other_diagnosis.nodes.workflow_nodes.get_kb_client",
        lambda: _FakeKB(),
    )
    build_graph.cache_clear()
    discover_workflows()
    out = executor.invoke(
        "other_diagnosis",
        {
            "discharge_diagnosis": '["急性心肌梗死","慢性胃炎"]',
            "main_diagnosis": "急性心肌梗死",
        },
    )
    assert out["workflow_id"] == "other_diagnosis"
    assert out["result"]["other_diagnosis"]
