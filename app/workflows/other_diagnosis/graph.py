from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows.other_diagnosis.nodes.workflow_nodes import (
    node_extract_other_diagnosis,
    node_iterate_knowledge,
    node_parse_discharge_list,
)
from app.workflows.other_diagnosis.state import OtherDiagnosisState


def _build() -> CompiledStateGraph:
    graph = StateGraph(OtherDiagnosisState)
    graph.add_node("parse_discharge_list", node_parse_discharge_list)
    graph.add_node("iterate_knowledge", node_iterate_knowledge)
    graph.add_node("extract_other_diagnosis", node_extract_other_diagnosis)

    graph.add_edge(START, "parse_discharge_list")
    graph.add_edge("parse_discharge_list", "iterate_knowledge")
    graph.add_edge("iterate_knowledge", "extract_other_diagnosis")
    graph.add_edge("extract_other_diagnosis", END)
    return graph.compile()


@lru_cache(maxsize=1)
def build_graph() -> CompiledStateGraph:
    return _build()
