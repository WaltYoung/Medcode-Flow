from __future__ import annotations

from app.runtime.registry import WorkflowSpec, registry
from app.workflows.secondary_diagnosis.graph import build_graph
from app.workflows.secondary_diagnosis.schemas import (
    SecondaryDiagnosisRequest,
    SecondaryDiagnosisResult,
)

WORKFLOW_ID = "secondary_diagnosis"
VERSION = "8.0.0"


def _input_mapper(request: SecondaryDiagnosisRequest) -> dict:
    return {"raw_medical_record": request.raw_medical_record}


def _output_mapper(state: dict) -> SecondaryDiagnosisResult:
    return SecondaryDiagnosisResult(
        main_diagnosis=state.get("main_diagnosis_normalized") or "",
        secondary_diagnosis=state.get("secondary_diagnosis") or "",
        main_diagnosis_keywords=state.get("main_diagnosis_keywords") or "",
        kb_contents=state.get("kb_result_json") or "",
    )


registry.register(
    WorkflowSpec(
        workflow_id=WORKFLOW_ID,
        name="次要诊断生成",
        version=VERSION,
        description=(
            "对齐 Dify【生产-V8】病案编码-02生成结果-次要诊断；"
            "知识库 127.0.0.1:8090；内部调用 other_diagnosis 子工作流"
        ),
        build_graph=build_graph,
        request_model=SecondaryDiagnosisRequest,
        response_model=SecondaryDiagnosisResult,
        input_mapper=_input_mapper,
        output_mapper=_output_mapper,
    )
)
