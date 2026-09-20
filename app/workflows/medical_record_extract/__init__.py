from __future__ import annotations

from app.runtime.registry import WorkflowSpec, registry
from app.workflows.medical_record_extract.graph import build_graph
from app.workflows.medical_record_extract.schemas import (
    MedicalRecordExtractRequest,
    MedicalRecordExtractResult,
)
from app.workflows.medical_record_extract.state import MedicalRecordExtractState

WORKFLOW_ID = "medical_record_extract"
VERSION = "8.0.0"


def _input_mapper(request: MedicalRecordExtractRequest) -> MedicalRecordExtractState:
    return {"raw_medical_record": request.raw_medical_record}


def _output_mapper(state: dict) -> MedicalRecordExtractResult:
    return MedicalRecordExtractResult(
        medical_summary=state.get("medical_summary") or "",
        has_history_diagnosis=state.get("has_history_diagnosis") or "",
        is_first_antitumor=state.get("is_first_antitumor") or "",
        abandon_original_plan=state.get("abandon_original_plan") or "",
        malignant_location=state.get("malignant_location") or "",
        diagnosis_list=state.get("diagnosis_list") or "",
        treatment_methods=state.get("treatment_methods") or "",
    )


registry.register(
    WorkflowSpec(
        workflow_id=WORKFLOW_ID,
        name="病历信息提取",
        version=VERSION,
        description="对齐 Dify【生产-V8】01 病历信息提取",
        build_graph=build_graph,
        request_model=MedicalRecordExtractRequest,
        response_model=MedicalRecordExtractResult,
        input_mapper=_input_mapper,
        output_mapper=_output_mapper,
    )
)
