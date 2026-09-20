from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows.medical_record_extract.nodes.llm_nodes import (
    node_abandon_or_skip,
    node_diagnosis_list,
    node_distribution_type,
    node_has_history_diagnosis,
    node_init,
    node_is_first_antitumor,
    node_location_consistency,
    node_malignant_location,
    node_sublocation,
    node_treatment_methods,
    node_tumor_info,
)
from app.workflows.medical_record_extract.nodes.preprocess import (
    node_current_time,
    node_simplify_record,
)
from app.workflows.medical_record_extract.state import MedicalRecordExtractState


def _build() -> CompiledStateGraph:
    graph = StateGraph(MedicalRecordExtractState)

    graph.add_node("current_time", node_current_time)
    graph.add_node("simplify_record", node_simplify_record)
    graph.add_node("init", node_init)
    graph.add_node("has_history_diagnosis", node_has_history_diagnosis)
    graph.add_node("is_first_antitumor", node_is_first_antitumor)
    graph.add_node("abandon_or_skip", node_abandon_or_skip)
    graph.add_node("tumor_info", node_tumor_info)
    graph.add_node("malignant_location", node_malignant_location)
    graph.add_node("sublocation", node_sublocation)
    graph.add_node("location_consistency", node_location_consistency)
    graph.add_node("distribution_type", node_distribution_type)
    graph.add_node("diagnosis_list", node_diagnosis_list)
    graph.add_node("treatment_methods", node_treatment_methods)

    graph.add_edge(START, "current_time")
    graph.add_edge("current_time", "simplify_record")
    graph.add_edge("simplify_record", "init")

    graph.add_edge("init", "has_history_diagnosis")
    graph.add_edge("init", "is_first_antitumor")
    graph.add_edge("init", "abandon_or_skip")

    graph.add_edge("has_history_diagnosis", "tumor_info")
    graph.add_edge("is_first_antitumor", "tumor_info")
    graph.add_edge("abandon_or_skip", "tumor_info")

    graph.add_edge("tumor_info", "malignant_location")
    graph.add_edge("malignant_location", "sublocation")
    graph.add_edge("sublocation", "location_consistency")
    graph.add_edge("location_consistency", "distribution_type")
    graph.add_edge("distribution_type", "diagnosis_list")
    graph.add_edge("diagnosis_list", "treatment_methods")
    graph.add_edge("treatment_methods", END)
    return graph.compile()


@lru_cache(maxsize=1)
def build_graph() -> CompiledStateGraph:
    return _build()
