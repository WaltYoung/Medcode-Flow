from __future__ import annotations

import json

from app.workflows.medical_record_extract.nodes._simplify_logic import main as simplify_main
from app.workflows.medical_record_extract.state import MedicalRecordExtractState


def node_current_time(state: MedicalRecordExtractState) -> dict:
    from app.shared.nodes.time import get_current_time

    return {"current_time": get_current_time()}


def node_simplify_record(state: MedicalRecordExtractState) -> dict:
    raw = state.get("raw_medical_record") or ""
    try:
        result = simplify_main(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "raw_medical_record 必须是 Dify 同款 JSON 数组字符串"
        ) from exc
    return {
        "simplified_text": result.get("text", ""),
        "ryrq": result.get("ryrq", "") or "",
        "cyrq": result.get("cyrq", "") or "",
        "zljg": result.get("zljg", "") or "",
        "sample_records": result.get("sample_records", "") or "",
        "ryjl": result.get("ryjl", "") or "",
        "yz": result.get("yz", "") or "",
    }
