from __future__ import annotations

from app.runtime.registry import WorkflowSpec, registry
from app.workflows.other_diagnosis.graph import build_graph
from app.workflows.other_diagnosis.schemas import (
    OtherDiagnosisRequest,
    OtherDiagnosisResult,
)

WORKFLOW_ID = "other_diagnosis"
VERSION = "1.0.0"


def _input_mapper(request: OtherDiagnosisRequest) -> dict:
    return {
        "discharge_diagnosis": request.discharge_diagnosis,
        "main_diagnosis": request.main_diagnosis,
    }


def _output_mapper(state: dict) -> OtherDiagnosisResult:
    return OtherDiagnosisResult(
        other_diagnosis=state.get("other_diagnosis") or "",
    )


registry.register(
    WorkflowSpec(
        workflow_id=WORKFLOW_ID,
        name="其他诊断提取",
        version=VERSION,
        description="对齐 Dify【生产】病案编码-工具-其他诊断工作流；知识库调用 127.0.0.1:8090",
        build_graph=build_graph,
        request_model=OtherDiagnosisRequest,
        response_model=OtherDiagnosisResult,
        input_mapper=_input_mapper,
        output_mapper=_output_mapper,
    )
)
