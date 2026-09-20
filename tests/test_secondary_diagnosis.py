from app.runtime.bootstrap import discover_workflows
from app.runtime.executor import executor
from app.runtime.registry import registry
from app.workflows.secondary_diagnosis.graph import build_graph
from app.workflows.secondary_diagnosis.nodes.logic import (
    extract_field_by_label,
    merge_keywords,
    parse_discharge_list,
    structure_keywords,
)


def test_logic_helpers():
    assert extract_field_by_label("肿瘤分布类型：交搭跨越\n是否随诊：否", "肿瘤分布类型") == "交搭跨越"
    assert "慢性胃炎" in parse_discharge_list('```json\n["肺腺癌","慢性胃炎"]\n```')
    structured = structure_keywords('```json\n["肺","上叶"]\n```')
    assert structured["zd_list"] == ["肺", "上叶"]
    assert merge_keywords(["肺", "上叶"], "食管中段 -> 食管") == ["食管"]


def test_secondary_diagnosis_registered():
    discover_workflows()
    assert "secondary_diagnosis" in registry
    assert "other_diagnosis" in registry


def test_secondary_diagnosis_graph(monkeypatch):
    class FakeKB:
        def search(self, query: str, **kwargs):
            return [
                {
                    "diag_code": "C34.900",
                    "diag_name": "肺恶性肿瘤",
                    "evidence": "肺",
                    "matched_keywords": [],
                }
            ]

    monkeypatch.setattr(
        "app.workflows.secondary_diagnosis.nodes.workflow_nodes.get_kb_client",
        lambda: FakeKB(),
    )
    monkeypatch.setattr(
        "app.workflows.secondary_diagnosis.nodes.workflow_nodes.call_other_diagnosis_workflow",
        lambda **kwargs: "# 其他诊断：\n- 慢性胃炎 K29.500",
    )
    # other_diagnosis may still be invoked nowhere due to patch
    build_graph.cache_clear()
    graph = build_graph()
    state = graph.invoke(
        {
            "raw_medical_record": json_record(),
        }
    )
    assert state["main_diagnosis_normalized"]
    assert "慢性胃炎" in state["secondary_diagnosis"]
    assert state["discharge_list_json"]
    assert state["kb_result_json"]


def test_secondary_diagnosis_executor(monkeypatch):
    monkeypatch.setattr(
        "app.workflows.secondary_diagnosis.nodes.workflow_nodes.get_kb_client",
        lambda: type(
            "KB",
            (),
            {
                "search": staticmethod(
                    lambda query, **kwargs: [
                        {
                            "diag_code": "C34.900",
                            "diag_name": "肺恶性肿瘤",
                            "evidence": query,
                            "matched_keywords": [],
                        }
                    ]
                )
            },
        )(),
    )
    monkeypatch.setattr(
        "app.workflows.secondary_diagnosis.nodes.workflow_nodes.call_other_diagnosis_workflow",
        lambda **kwargs: "# 其他诊断：\n- 高血压 I10",
    )
    build_graph.cache_clear()
    discover_workflows()
    out = executor.invoke(
        "secondary_diagnosis",
        {"raw_medical_record": json_record()},
    )
    assert out["workflow_id"] == "secondary_diagnosis"
    assert out["result"]["main_diagnosis"]
    assert out["result"]["secondary_diagnosis"]


def json_record() -> str:
    return (
        '[{"title":"出院记录","content":{"出院诊断":"1.肺腺癌 2.慢性胃炎"}},'
        '{"title":"入院记录","content":{"主诉":"咳嗽"}}]'
    )
