from __future__ import annotations

import json
import logging
from typing import Any

from app.shared.kb.client import get_kb_client, search_results_to_knowledges
from app.workflows.secondary_diagnosis.nodes.logic import (
    extract_field_by_label,
    flatten_kb_contents,
    merge_keywords,
    parse_discharge_list,
    parse_json_array,
    structure_keywords,
)
from app.workflows.secondary_diagnosis.nodes.llm_utils import (
    invoke_llm,
    render_and_invoke,
)
from app.workflows.secondary_diagnosis.state import SecondaryDiagnosisState

logger = logging.getLogger(__name__)


def _pex_instruction() -> str:
    from pathlib import Path

    path = (
        Path(__file__).resolve().parent.parent
        / "prompts"
        / "pex_tumor_site_instruction.md"
    )
    return path.read_text(encoding="utf-8")


def node_select_main(state: SecondaryDiagnosisState) -> dict:
    text = render_and_invoke(
        system_name="01_select_main_system.md",
        user_name="01_select_main_user.md",
        variables={"raw_medical_record": state.get("raw_medical_record") or ""},
        mock_hint="选择主要诊断",
        mock_output=(
            "主要诊断：肺腺癌\n肿瘤分布类型：单发\n是否随诊：否\n"
        ),
    )
    return {"main_diagnosis_raw": text}


def node_extract_discharge(state: SecondaryDiagnosisState) -> dict:
    text = render_and_invoke(
        system_name="02_extract_discharge_system.md",
        user_name="02_extract_discharge_user.md",
        variables={"raw_medical_record": state.get("raw_medical_record") or ""},
        mock_hint="出院诊断",
        mock_output='```json\n["肺腺癌","慢性胃炎","高血压病"]\n```',
    )
    return {"discharge_raw": text}


def node_parse_discharge(state: SecondaryDiagnosisState) -> dict:
    return {
        "discharge_list_json": parse_discharge_list(state.get("discharge_raw") or "")
    }


def node_keyword_pipeline(state: SecondaryDiagnosisState) -> dict:
    """复刻：分布类型/随诊/交搭分支 + 关键词 LLM + 模板聚合 + 结构化。"""
    main_raw = state.get("main_diagnosis_raw") or ""
    record = state.get("raw_medical_record") or ""

    fblx = extract_field_by_label(main_raw, "肿瘤分布类型")
    is_sz = extract_field_by_label(main_raw, "是否随诊")

    keywords_normal = ""
    keywords_overlap_a = ""
    keywords_overlap_b = ""
    keywords_followup = ""
    jdmb = ""

    if "交搭" in (fblx or ""):
        overlap_text = render_and_invoke(
            system_name="04_is_overlap_system.md",
            user_name="04_is_overlap_user.md",
            variables={"main_diagnosis_raw": main_raw},
            mock_hint="是否交搭",
            mock_output="应选择的分类模板：一",
        )
        jdmb = extract_field_by_label(overlap_text, "应选择的分类模板")
        if "一" in (jdmb or ""):
            keywords_overlap_a = render_and_invoke(
                system_name="05a_keywords_overlap_a_system.md",
                user_name="05a_keywords_overlap_a_user.md",
                variables={
                    "raw_medical_record": record,
                    "main_diagnosis_raw": main_raw,
                },
                mock_hint="交搭A",
                mock_output='```json\n["肺","上叶"]\n```',
            )
        else:
            keywords_overlap_b = render_and_invoke(
                system_name="05b_keywords_overlap_b_system.md",
                user_name="05b_keywords_overlap_b_user.md",
                variables={
                    "raw_medical_record": record,
                    "main_diagnosis_raw": main_raw,
                },
                mock_hint="交搭B",
                mock_output='```json\n["肺"]\n```',
            )
    elif "是" in (is_sz or ""):
        keywords_followup = render_and_invoke(
            system_name="05c_keywords_followup_system.md",
            user_name="05c_keywords_followup_user.md",
            variables={
                "raw_medical_record": record,
                "main_diagnosis_raw": main_raw,
            },
            mock_hint="随诊关键词",
            mock_output='```json\n["随诊检查"]\n```',
        )
    else:
        keywords_normal = render_and_invoke(
            system_name="03_keywords_normal_system.md",
            user_name="03_keywords_normal_user.md",
            variables={
                "raw_medical_record": record,
                "main_diagnosis_raw": main_raw,
            },
            mock_hint="主要诊断关键词",
            mock_output='```json\n["肺腺癌","肺"]\n```',
        )

    aggregated = (
        keywords_normal
        or keywords_overlap_a
        or keywords_overlap_b
        or keywords_followup
        or '["暂无数据"]'
    )
    structured = structure_keywords(aggregated)
    return {
        "fblx": fblx,
        "is_sz": is_sz,
        "jdmb": jdmb,
        "keywords_normal": keywords_normal,
        "keywords_overlap_a": keywords_overlap_a,
        "keywords_overlap_b": keywords_overlap_b,
        "keywords_followup": keywords_followup,
        "keywords_aggregated": aggregated,
        "zd_list": structured["zd_list"],
        "zd_list_str": structured["zd_list_str"],
        "main_diagnosis_keywords": keywords_normal or aggregated,
    }


def node_tumor_site_and_merge(state: SecondaryDiagnosisState) -> dict:
    """复刻：参数提取肿瘤器官 + 食管条件分支 + 关键词合并。"""
    main_raw = state.get("main_diagnosis_raw") or ""
    instruction = _pex_instruction()
    pex_user = (
        f"输入文本：\n{main_raw}\n\n"
        "请仅输出 tumor_site 的 JSON 数组（array[string]），例如 [\"肺\"] 或 []。"
    )
    pex_text = invoke_llm(
        system=instruction,
        user=pex_user,
        mock_hint="肿瘤所属器官",
        mock_output='["肺"]',
    )
    tumor_site = [str(x) for x in parse_json_array(pex_text)]

    esophagus_normalized = ""
    if any("食管" in str(site) for site in tumor_site):
        esophagus_normalized = render_and_invoke(
            system_name="06_esophagus_normalize_system.md",
            user_name="06_esophagus_normalize_user.md",
            variables={"zd_list_str": state.get("zd_list_str") or "[]"},
            mock_hint="食管",
            mock_output="食管中段 -> 食管",
        )

    kb_query_list = merge_keywords(state.get("zd_list"), esophagus_normalized)
    return {
        "tumor_site": tumor_site,
        "esophagus_normalized": esophagus_normalized,
        "kb_query_list": kb_query_list,
    }


def node_kb_iterate(state: SecondaryDiagnosisState) -> dict:
    """对齐迭代知识检索（Dify top_k=6）+ 提取知识库。"""
    kb = get_kb_client()
    collected: list[dict[str, Any]] = []
    for item in state.get("kb_query_list") or []:
        query = str(item).strip()
        if not query:
            continue
        try:
            results = kb.search(query, top_k=6)
        except Exception:
            logger.exception("kb_search_failed query=%s", query)
            results = []
        collected.extend(search_results_to_knowledges(results))

    return {
        "kb_iteration_output": collected,
        "kb_result_json": flatten_kb_contents(collected),
    }


def node_normalize_main(state: SecondaryDiagnosisState) -> dict:
    kb_query = state.get("kb_query_list") or []
    text = render_and_invoke(
        system_name="08_normalize_main_system.md",
        user_name="08_normalize_main_user.md",
        variables={
            "kb_query_list": json.dumps(kb_query, ensure_ascii=False),
            "kb_result_json": state.get("kb_result_json") or "[]",
        },
        mock_hint="规范主要诊断",
        mock_output="肺恶性肿瘤 C34.900",
    )
    return {"main_diagnosis_normalized": text}


def call_other_diagnosis_workflow(
    *,
    discharge_diagnosis: str,
    main_diagnosis: str,
) -> str:
    """调用已注册的 other_diagnosis 子工作流。"""
    from app.runtime.executor import executor

    out = executor.invoke(
        "other_diagnosis",
        {
            "discharge_diagnosis": discharge_diagnosis,
            "main_diagnosis": main_diagnosis,
        },
    )
    result = out.get("result") or {}
    return str(result.get("other_diagnosis") or "")


def node_call_other_diagnosis(state: SecondaryDiagnosisState) -> dict:
    other = call_other_diagnosis_workflow(
        discharge_diagnosis=state.get("discharge_list_json") or "[]",
        main_diagnosis=state.get("main_diagnosis_normalized") or "",
    )
    return {
        "other_diagnosis_raw": other,
        "secondary_diagnosis": other,
    }
