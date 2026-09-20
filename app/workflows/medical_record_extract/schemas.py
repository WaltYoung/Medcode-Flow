from __future__ import annotations

from pydantic import BaseModel, Field


class MedicalRecordExtractRequest(BaseModel):
    raw_medical_record: str = Field(
        ...,
        description="原始病历文本（通常为 JSON 字符串，与 Dify 输入一致）",
        min_length=1,
    )


class MedicalRecordExtractResult(BaseModel):
    medical_summary: str = Field("", description="病历摘要")
    has_history_diagnosis: str = Field("", description="是否存在历史确诊")
    is_first_antitumor: str = Field("", description="是否首次抗肿瘤治疗")
    abandon_original_plan: str = Field("", description="是否拟放弃原治疗计划")
    malignant_location: str = Field("", description="肿瘤位置")
    diagnosis_list: str = Field("", description="诊断清单")
    treatment_methods: str = Field("", description="治疗方式")


class MedicalRecordExtractResponse(BaseModel):
    workflow_id: str
    version: str
    trace_id: str
    latency_ms: int
    result: MedicalRecordExtractResult
