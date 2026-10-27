from __future__ import annotations

import logging
import uuid
from typing import Any

from app.runtime.registry import WorkflowSpec, registry
from app.runtime.traced_run import run_workflow

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
        trace = trace_id or str(uuid.uuid4())
        logger.info("workflow_start workflow_id=%s trace_id=%s", workflow_id, trace)
        outcome = run_workflow(spec, payload, trace_id=trace)
        logger.info(
            "workflow_done workflow_id=%s trace_id=%s status=%s latency_ms=%s",
            workflow_id,
            outcome.run_id,
            outcome.status,
            outcome.latency_ms,
        )
        if outcome.status != "succeeded":
            raise RuntimeError(outcome.error or "workflow failed")
        return {
            "workflow_id": workflow_id,
            "version": spec.version,
            "trace_id": outcome.run_id,
            "latency_ms": outcome.latency_ms,
            "result": outcome.english_result,
        }

    def get_spec(self, workflow_id: str) -> WorkflowSpec:
        return registry.get(workflow_id)


executor = WorkflowExecutor()
