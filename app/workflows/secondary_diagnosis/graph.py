from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows.secondary_diagnosis.nodes.workflow_nodes import (
    node_call_other_diagnosis,
    node_extract_discharge,
    node_kb_iterate,
    node_keyword_pipeline,
    node_normalize_main,
    node_parse_discharge,
    node_select_main,
    node_tumor_site_and_merge,
)
from app.workflows.secondary_diagnosis.state import SecondaryDiagnosisState


def _build() -> CompiledStateGraph:
    graph = StateGraph(SecondaryDiagnosisState)

    graph.add_node("select_main", node_select_main)
    graph.add_node("extract_discharge", node_extract_discharge)
    graph.add_node("parse_discharge", node_parse_discharge)
    graph.add_node("keyword_pipeline", node_keyword_pipeline)
    graph.add_node("tumor_site_and_merge", node_tumor_site_and_merge)
    graph.add_node("kb_iterate", node_kb_iterate)
    graph.add_node("normalize_main", node_normalize_main)
    graph.add_node("call_other_diagnosis", node_call_other_diagnosis)

    # 并行：主要诊断链路 + 出院诊断链路
    graph.add_edge(START, "select_main")
    graph.add_edge(START, "extract_discharge")

    graph.add_edge("select_main", "keyword_pipeline")
    graph.add_edge("keyword_pipeline", "tumor_site_and_merge")
    graph.add_edge("tumor_site_and_merge", "kb_iterate")
    graph.add_edge("kb_iterate", "normalize_main")

    graph.add_edge("extract_discharge", "parse_discharge")

    # 汇聚后调用 other_diagnosis：必须用 list 入边做 barrier，
    # 两条独立 add_edge 会在任一分支完成时就触发（出院分支更短），
    # 导致 main_diagnosis_normalized 仍为空并触发 OtherDiagnosisRequest 校验失败。
    graph.add_edge(["normalize_main", "parse_discharge"], "call_other_diagnosis")
    graph.add_edge("call_other_diagnosis", END)
    return graph.compile()


@lru_cache(maxsize=1)
def build_graph() -> CompiledStateGraph:
    return _build()
