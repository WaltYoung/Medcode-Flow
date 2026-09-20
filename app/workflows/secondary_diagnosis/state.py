from __future__ import annotations

from typing import Any, TypedDict


class SecondaryDiagnosisState(TypedDict, total=False):
    raw_medical_record: str

    # branch: select main
    main_diagnosis_raw: str
    fblx: str
    is_sz: str
    jdmb: str
    keywords_normal: str
    keywords_overlap_a: str
    keywords_overlap_b: str
    keywords_followup: str
    keywords_aggregated: str
    zd_list: list[Any]
    zd_list_str: str
    tumor_site: list[str]
    esophagus_normalized: str
    kb_query_list: list[Any]
    kb_result_json: str
    kb_iteration_output: list[dict[str, Any]]
    main_diagnosis_normalized: str
    main_diagnosis_keywords: str

    # branch: discharge
    discharge_raw: str
    discharge_list_json: str

    # join: other_diagnosis sub-workflow
    other_diagnosis_raw: str
    secondary_diagnosis: str
