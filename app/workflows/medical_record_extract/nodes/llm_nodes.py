from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_factory
from app.workflows.medical_record_extract.prompt_loader import render_prompt
from app.workflows.medical_record_extract.state import MedicalRecordExtractState

logger = logging.getLogger(__name__)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _invoke_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    output_key: str,
    mock_hint: str,
) -> dict[str, str]:
    llm = get_llm_factory().get(
        mock_responses={mock_hint: f"[mock]{output_key}"},
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return {output_key: str(content)}


def node_init(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "01_init_system.md",
        simplified_text=_as_str(state.get("simplified_text")),
    )
    user = render_prompt(
        "01_init_user.md",
        simplified_text=_as_str(state.get("simplified_text")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="medical_summary",
        mock_hint="病历预处理",
    )


def node_has_history_diagnosis(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "02_has_history_diagnosis_system.md",
        current_time=_as_str(state.get("current_time")),
        ryjl=_as_str(state.get("ryjl")),
    )
    user = render_prompt(
        "02_has_history_diagnosis_user.md",
        ryjl=_as_str(state.get("ryjl")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="has_history_diagnosis",
        mock_hint="历史确诊",
    )


def node_is_first_antitumor(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "03_is_first_antitumor_system.md",
        current_time=_as_str(state.get("current_time")),
        ryjl=_as_str(state.get("ryjl")),
        yz=_as_str(state.get("yz")),
    )
    user = render_prompt(
        "03_is_first_antitumor_user.md",
        ryjl=_as_str(state.get("ryjl")),
        yz=_as_str(state.get("yz")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="is_first_antitumor",
        mock_hint="首次抗肿瘤",
    )


def node_abandon_or_skip(state: MedicalRecordExtractState) -> dict:
    """Align with Dify if-else: skip LLM when zljg is empty."""
    zljg = (_as_str(state.get("zljg"))).strip()
    if not zljg:
        return {"abandon_original_plan": ""}
    system = render_prompt(
        "04_abandon_original_plan_system.md",
        zljg=zljg,
    )
    user = render_prompt(
        "04_abandon_original_plan_user.md",
        zljg=zljg,
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="abandon_original_plan",
        mock_hint="放弃拟治疗",
    )


def node_tumor_info(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "05_tumor_info_system.md",
        simplified_text=_as_str(state.get("simplified_text")),
    )
    user = render_prompt(
        "05_tumor_info_user.md",
        simplified_text=_as_str(state.get("simplified_text")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="tumor_info",
        mock_hint="肿瘤病历信息提取",
    )


def node_malignant_location(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "06_malignant_location_system.md",
        simplified_text=_as_str(state.get("simplified_text")),
        tumor_info=_as_str(state.get("tumor_info")),
    )
    user = render_prompt(
        "06_malignant_location_user.md",
        simplified_text=_as_str(state.get("simplified_text")),
        tumor_info=_as_str(state.get("tumor_info")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="malignant_location",
        mock_hint="恶性病灶位置",
    )


def node_sublocation(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "07_sublocation_system.md",
        malignant_location=_as_str(state.get("malignant_location")),
    )
    user = render_prompt(
        "07_sublocation_user.md",
        malignant_location=_as_str(state.get("malignant_location")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="sublocation",
        mock_hint="亚部位",
    )


def node_location_consistency(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "08_location_consistency_system.md",
        sublocation=_as_str(state.get("sublocation")),
    )
    user = render_prompt(
        "08_location_consistency_user.md",
        sublocation=_as_str(state.get("sublocation")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="location_consistency",
        mock_hint="病灶位置一致性",
    )


def node_distribution_type(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "09_distribution_type_system.md",
        malignant_location=_as_str(state.get("malignant_location")),
        location_consistency=_as_str(state.get("location_consistency")),
    )
    user = render_prompt(
        "09_distribution_type_user.md",
        malignant_location=_as_str(state.get("malignant_location")),
        location_consistency=_as_str(state.get("location_consistency")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="distribution_type",
        mock_hint="分布类型",
    )


def node_diagnosis_list(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "10_diagnosis_list_system.md",
        simplified_text=_as_str(state.get("simplified_text")),
        malignant_location=_as_str(state.get("malignant_location")),
    )
    user = render_prompt(
        "10_diagnosis_list_user.md",
        simplified_text=_as_str(state.get("simplified_text")),
        malignant_location=_as_str(state.get("malignant_location")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="diagnosis_list",
        mock_hint="诊断列表",
    )


def node_treatment_methods(state: MedicalRecordExtractState) -> dict:
    system = render_prompt(
        "11_treatment_methods_system.md",
        ryrq=_as_str(state.get("ryrq")),
        cyrq=_as_str(state.get("cyrq")),
        sample_records=_as_str(state.get("sample_records")),
    )
    user = render_prompt(
        "11_treatment_methods_user.md",
        sample_records=_as_str(state.get("sample_records")),
    )
    return _invoke_llm(
        system_prompt=system,
        user_prompt=user,
        output_key="treatment_methods",
        mock_hint="治疗方式",
    )
