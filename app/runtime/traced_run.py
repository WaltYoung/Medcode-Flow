"""按节点执行图，并记下每一步。"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.runtime.node_titles import node_title
from app.runtime.registry import WorkflowSpec
from app.runtime.run_store import append_node, create_run, finish_run, get_run

_SKIP = {"__start__", "__end__", "START", "END"}

_EXTRACT_CN = {
    "medical_summary": "病历概要",
    "has_history_diagnosis": "是否存在历史确诊",
    "is_first_antitumor": "是否首次抗肿瘤治疗",
    "abandon_original_plan": "是否拟放弃原治疗计划",
    "malignant_location": "肿瘤位置",
    "diagnosis_list": "诊断清单",
    "treatment_methods": "治疗方式",
}

_SECONDARY_CN = {
    "main_diagnosis": "主要诊断",
    "secondary_diagnosis": "次要诊断",
    "main_diagnosis_keywords": "主要诊断关键词",
    "kb_contents": "提取的知识库内容",
}


@dataclass
class RunOutcome:
    run_id: str
    task_id: str
    workflow_id: str
    version: str
    status: str
    outputs: dict[str, Any]
    english_result: dict[str, Any]
    error: str | None
    elapsed_time: float
    latency_ms: int
    total_steps: int
    created_at: int
    finished_at: int | None
    tracing: list[dict[str, Any]] = field(default_factory=list)


def to_public_outputs(workflow_id: str, result: BaseModel) -> dict[str, Any]:
    data = result.model_dump()
    mapping = {
        "medical_record_extract": _EXTRACT_CN,
        "secondary_diagnosis": _SECONDARY_CN,
    }.get(workflow_id)
    if mapping is None:
        return data
    return {cn: data.get(en, "") for en, cn in mapping.items()}


def run_workflow(
    spec: WorkflowSpec,
    payload: dict[str, Any],
    *,
    user_id: str = "",
    trace_id: str | None = None,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> RunOutcome:
    def emit(event: str, payload_event: dict[str, Any]) -> None:
        if on_event is not None:
            on_event(event, payload_event)
    request = spec.request_model.model_validate(payload)
    graph_input = spec.input_mapper(request)
    run_id = trace_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    created_at = create_run(
        run_id=run_id,
        task_id=task_id,
        workflow_id=spec.workflow_id,
        user_id=user_id,
        inputs=payload,
    )
    base = {"workflow_run_id": run_id, "task_id": task_id}
    emit(
        "workflow_started",
        {
            **base,
            "data": {
                "id": run_id,
                "workflow_id": spec.workflow_id,
                "created_at": created_at,
            },
        },
    )
    started = time.perf_counter()
    prev = started
    state: dict[str, Any] = dict(graph_input)
    index = 0
    real_steps = 0
    start_row = append_node(
        run_id=run_id,
        node_id="start",
        title="开始",
        index_no=index,
        status="succeeded",
        inputs={},
        outputs=payload,
        elapsed_time=0,
    )
    emit("node_started", {**base, "data": {"node_id": "start", "title": "开始"}})
    emit("node_finished", {**base, "data": start_row})
    index += 1
    try:
        graph = spec.build_graph()
        for update in graph.stream(graph_input, stream_mode="updates"):
            now = time.perf_counter()
            if not isinstance(update, dict):
                prev = now
                continue
            items = [(name, partial) for name, partial in update.items() if name not in _SKIP]
            share = (now - prev) / len(items) if items else 0.0
            for name, partial in items:
                outputs = partial if isinstance(partial, dict) else {"value": partial}
                title = node_title(spec.workflow_id, name)
                emit("node_started", {**base, "data": {"node_id": name, "title": title}})
                node_row = append_node(
                    run_id=run_id,
                    node_id=name,
                    title=title,
                    index_no=index,
                    status="succeeded",
                    inputs=dict(state),
                    outputs=outputs,
                    elapsed_time=round(share, 6),
                )
                emit("node_finished", {**base, "data": node_row})
                state.update(outputs)
                index += 1
                real_steps += 1
            prev = now
        result = spec.output_mapper(state)
        outputs = to_public_outputs(spec.workflow_id, result)
        end_row = append_node(
            run_id=run_id,
            node_id="end",
            title="结束",
            index_no=index,
            status="succeeded",
            inputs=outputs,
            outputs=outputs,
            elapsed_time=0,
        )
        emit("node_started", {**base, "data": {"node_id": "end", "title": "结束"}})
        emit("node_finished", {**base, "data": end_row})
        elapsed = round(time.perf_counter() - started, 6)
        finish_run(
            run_id=run_id,
            status="succeeded",
            outputs=outputs,
            total_steps=real_steps,
            elapsed_time=elapsed,
        )
        stored = get_run(run_id) or {}
        return RunOutcome(
            run_id=run_id,
            task_id=task_id,
            workflow_id=spec.workflow_id,
            version=spec.version,
            status="succeeded",
            outputs=outputs,
            english_result=result.model_dump(),
            error=None,
            elapsed_time=elapsed,
            latency_ms=int(elapsed * 1000),
            total_steps=real_steps,
            created_at=created_at,
            finished_at=stored.get("finished_at"),
            tracing=stored.get("tracing") or [],
        )
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 6)
        append_node(
            run_id=run_id,
            node_id="failed",
            title="执行失败",
            index_no=index,
            status="failed",
            inputs=dict(state),
            outputs={},
            elapsed_time=0,
            error=str(exc),
        )
        finish_run(
            run_id=run_id,
            status="failed",
            outputs={},
            total_steps=real_steps,
            elapsed_time=elapsed,
            error=str(exc),
        )
        stored = get_run(run_id) or {}
        return RunOutcome(
            run_id=run_id,
            task_id=task_id,
            workflow_id=spec.workflow_id,
            version=spec.version,
            status="failed",
            outputs={},
            english_result={},
            error=str(exc),
            elapsed_time=elapsed,
            latency_ms=int(elapsed * 1000),
            total_steps=real_steps,
            created_at=created_at,
            finished_at=stored.get("finished_at"),
            tracing=stored.get("tracing") or [],
        )
