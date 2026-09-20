from __future__ import annotations

from pydantic import BaseModel, Field


class SecondaryDiagnosisRequest(BaseModel):
    raw_medical_record: str = Field(
        ...,
        description="原始病历文本（通常为 JSON 字符串）",
        min_length=1,
    )


class SecondaryDiagnosisResult(BaseModel):
    main_diagnosis: str = Field("", description="主要诊断（规范后）")
    secondary_diagnosis: str = Field("", description="次要诊断（其他诊断）")
    main_diagnosis_keywords: str = Field("", description="主要诊断关键词")
    kb_contents: str = Field("", description="提取的知识库内容 JSON")


class SecondaryDiagnosisResponse(BaseModel):
    workflow_id: str
    version: str
    trace_id: str
    latency_ms: int
    result: SecondaryDiagnosisResult
