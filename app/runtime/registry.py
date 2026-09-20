from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    name: str
    version: str
    description: str
    build_graph: Callable[[], CompiledStateGraph]
    request_model: type[BaseModel]
    response_model: type[BaseModel]
    input_mapper: Callable[[BaseModel], dict[str, Any]]
    output_mapper: Callable[[dict[str, Any]], BaseModel]


class WorkflowRegistry:
    def __init__(self) -> None:
        self._items: dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> None:
        if spec.workflow_id in self._items:
            raise ValueError(f"Workflow already registered: {spec.workflow_id}")
        self._items[spec.workflow_id] = spec

    def get(self, workflow_id: str) -> WorkflowSpec:
        try:
            return self._items[workflow_id]
        except KeyError as exc:
            raise KeyError(f"Unknown workflow_id: {workflow_id}") from exc

    def list(self) -> list[WorkflowSpec]:
        return list(self._items.values())

    def __contains__(self, workflow_id: str) -> bool:
        return workflow_id in self._items


registry = WorkflowRegistry()
