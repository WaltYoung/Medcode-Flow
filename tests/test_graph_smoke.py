from app.runtime.bootstrap import discover_workflows
from app.runtime.executor import executor
from app.runtime.registry import registry
from app.workflows.medical_record_extract.graph import build_graph
from tests.conftest import sample_record_json


def test_graph_compiles_and_runs_with_mock_llm():
    graph = build_graph()
    state = graph.invoke({"raw_medical_record": sample_record_json()})
    assert state["current_time"]
    assert state["ryrq"] == "2024-01-01"
    assert "medical_summary" in state
    assert "has_history_diagnosis" in state
    assert "is_first_antitumor" in state
    assert state.get("abandon_original_plan") is not None
    assert "treatment_methods" in state


def test_workflow_is_registered():
    discover_workflows()
    spec = registry.get("medical_record_extract")
    assert spec.version == "8.0.0"


def test_executor_invoke():
    discover_workflows()
    out = executor.invoke(
        "medical_record_extract",
        {"raw_medical_record": sample_record_json()},
    )
    assert out["workflow_id"] == "medical_record_extract"
    assert "result" in out
    assert "trace_id" in out
    assert out["latency_ms"] >= 0
