from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.runtime.registry import WorkflowSpec, registry

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    def invoke(
        self,
        workflow_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        spec = registry.get(workflow_id)
        request = spec.request_model.model_validate(payload)
        graph_input = spec.input_mapper(request)
        trace = trace_id or str(uuid.uuid4())
        started = time.perf_counter()
        logger.info(
            "workflow_start workflow_id=%s trace_id=%s",
            workflow_id,
            trace,
        )
        graph = spec.build_graph()
        raw = graph.invoke(graph_input)
        latency_ms = int((time.perf_counter() - started) * 1000)
        result = spec.output_mapper(raw)
        logger.info(
            "workflow_done workflow_id=%s trace_id=%s latency_ms=%s",
            workflow_id,
            trace,
            latency_ms,
        )
        return {
            "workflow_id": workflow_id,
            "version": spec.version,
            "trace_id": trace,
            "latency_ms": latency_ms,
            "result": result.model_dump(),
        }

    def get_spec(self, workflow_id: str) -> WorkflowSpec:
        return registry.get(workflow_id)


executor = WorkflowExecutor()
