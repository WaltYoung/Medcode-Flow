from __future__ import annotations

from pydantic import BaseModel, Field


class OtherDiagnosisRequest(BaseModel):
    discharge_diagnosis: str = Field(
        ...,
        description='出院诊断列表 JSON 字符串，如 ["急性心肌梗死","慢性胃炎"]',
        min_length=1,
    )
    main_diagnosis: str = Field(
        ...,
        description="主要诊断名称",
        min_length=1,
    )


class OtherDiagnosisResult(BaseModel):
    other_diagnosis: str = Field("", description="其他诊断（含 ICD10 编码）")


class OtherDiagnosisResponse(BaseModel):
    workflow_id: str
    version: str
    trace_id: str
    latency_ms: int
    result: OtherDiagnosisResult
