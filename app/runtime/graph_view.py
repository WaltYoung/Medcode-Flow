"""把已注册的 LangGraph 图转成前端可画的节点和连线。"""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.runtime.node_titles import node_title
from app.runtime.registry import registry

# kind: llm 调模型，code 纯逻辑，kb 查知识库，workflow 调用子工作流
_META: dict[str, dict[str, tuple[str, str | None]]] = {
    "medical_record_extract": {
        "current_time": ("code", None),
        "simplify_record": ("code", None),
        "init": ("llm", "01_init_system.md"),
        "has_history_diagnosis": ("llm", "02_has_history_diagnosis_system.md"),
        "is_first_antitumor": ("llm", "03_is_first_antitumor_system.md"),
        "abandon_or_skip": ("llm", "04_abandon_original_plan_system.md"),
        "tumor_info": ("llm", "05_tumor_info_system.md"),
        "malignant_location": ("llm", "06_malignant_location_system.md"),
        "sublocation": ("llm", "07_sublocation_system.md"),
        "location_consistency": ("llm", "08_location_consistency_system.md"),
        "distribution_type": ("llm", "09_distribution_type_system.md"),
        "diagnosis_list": ("llm", "10_diagnosis_list_system.md"),
        "treatment_methods": ("llm", "11_treatment_methods_system.md"),
    },
    "secondary_diagnosis": {
        "select_main": ("llm", "01_select_main_system.md"),
        "extract_discharge": ("llm", "02_extract_discharge_system.md"),
        "parse_discharge": ("code", None),
        "keyword_pipeline": ("llm", "03_keywords_normal_system.md"),
        "tumor_site_and_merge": ("llm", "pex_tumor_site_instruction.md"),
        "kb_iterate": ("kb", None),
        "normalize_main": ("llm", "08_normalize_main_system.md"),
        "call_other_diagnosis": ("workflow", None),
    },
    "other_diagnosis": {
        "parse_discharge_list": ("code", None),
        "iterate_knowledge": ("kb", None),
        "extract_other_diagnosis": ("llm", "extract_other_system.md"),
    },
}

_KIND_LABEL = {
    "llm": "LLM",
    "code": "代码",
    "kb": "知识库",
    "workflow": "子工作流",
    "start": "开始",
    "end": "结束",
}


def _read_prompt(workflow_id: str, filename: str | None) -> str:
    if not filename:
        return ""
    path = (
        Path(__file__).resolve().parents[1]
        / "workflows"
        / workflow_id
        / "prompts"
        / filename
    )
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_graph_view(workflow_id: str) -> dict:
    spec = registry.get(workflow_id)
    drawable = spec.build_graph().get_graph()
    settings = get_settings()
    meta = _META.get(workflow_id, {})
    nodes: list[dict] = []
    for node_id in drawable.nodes:
        if node_id == "__start__":
            kind, prompt_file = "start", None
            title = "开始"
        elif node_id == "__end__":
            kind, prompt_file = "end", None
            title = "结束"
        else:
            kind, prompt_file = meta.get(node_id, ("code", None))
            title = node_title(workflow_id, node_id)
        nodes.append(
            {
                "id": node_id,
                "title": title,
                "kind": kind,
                "kind_label": _KIND_LABEL.get(kind, kind),
                "prompt": _read_prompt(workflow_id, prompt_file),
            }
        )
    edges = [
        {"source": edge.source, "target": edge.target}
        for edge in drawable.edges
        if edge.source and edge.target
    ]
    # 与真实调用一致：hospital 用 hospital_llm_model，其余用 llm_model
    if settings.llm_provider == "mock":
        model = ""
    elif settings.llm_provider == "hospital":
        model = (settings.hospital_llm_model or settings.llm_model or "").strip()
    else:
        model = (settings.llm_model or "").strip()
    return {
        "workflow_id": spec.workflow_id,
        "name": spec.name,
        "version": spec.version,
        "description": spec.description,
        "model": model,
        "nodes": nodes,
        "edges": edges,
    }
