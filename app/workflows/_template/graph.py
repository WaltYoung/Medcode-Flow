from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.workflows._template.state import TemplateState


def _echo(state: TemplateState) -> dict:
    return {"echo": state.get("text") or ""}


@lru_cache(maxsize=1)
def build_graph() -> CompiledStateGraph:
    graph = StateGraph(TemplateState)
    graph.add_node("echo", _echo)
    graph.add_edge(START, "echo")
    graph.add_edge("echo", END)
    return graph.compile()
