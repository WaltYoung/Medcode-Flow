from __future__ import annotations

from typing import Any, TypedDict


class MedicalRecordExtractState(TypedDict, total=False):
    raw_medical_record: str
    current_time: str

    # simplify_record outputs
    simplified_text: str
    ryrq: str
    cyrq: str
    zljg: str
    sample_records: str
    ryjl: str
    yz: str

    # llm outputs
    medical_summary: str
    has_history_diagnosis: str
    is_first_antitumor: str
    abandon_original_plan: str
    tumor_info: str
    malignant_location: str
    sublocation: str
    location_consistency: str
    distribution_type: str
    diagnosis_list: str
    treatment_methods: str

    errors: list[dict[str, Any]]
