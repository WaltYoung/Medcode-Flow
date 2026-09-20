from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_factory
from app.shared.kb.client import get_kb_client, search_results_to_knowledges
from app.workflows.other_diagnosis.nodes.logic import (
    extract_knowledge_for_diagnosis,
    parse_discharge_diagnosis_list,
)
from app.workflows.other_diagnosis.prompt_loader import render_prompt
from app.workflows.other_diagnosis.state import OtherDiagnosisState

logger = logging.getLogger(__name__)


def node_parse_discharge_list(state: OtherDiagnosisState) -> dict:
    cyzd_list = parse_discharge_diagnosis_list(state.get("discharge_diagnosis") or "")
    return {"cyzd_list": cyzd_list}


def node_iterate_knowledge(state: OtherDiagnosisState) -> dict:
    """串行迭代：对每个出院诊断调用知识库并过滤（对齐 Dify iteration）。"""
    kb = get_kb_client()
    iteration_output: list[dict[str, Any]] = []
    context_chunks: list[str] = []

    for name in state.get("cyzd_list") or []:
        try:
            results = kb.search(name)
        except Exception:
            logger.exception("kb_search_item_failed name=%s", name)
            results = []

        knowledges = search_results_to_knowledges(results)
        filtered = extract_knowledge_for_diagnosis(knowledges, name)

        # 若精确行过滤为空，回退使用检索原始结构化条目，避免上下文完全缺失
        if not filtered and knowledges:
            filtered = knowledges

        iteration_output.append(
            {
                "diagnosis": name,
                "result": filtered,
                "raw_hits": results,
            }
        )
        for item in filtered:
            content = (item.get("content") or "").strip()
            if content:
                context_chunks.append(content)

    return {
        "iteration_output": iteration_output,
        "kb_context": "\n".join(context_chunks),
    }


def node_extract_other_diagnosis(state: OtherDiagnosisState) -> dict:
    system = render_prompt(
        "extract_other_system.md",
        kb_context=state.get("kb_context") or "",
    )
    user = render_prompt(
        "extract_other_user.md",
        discharge_diagnosis=state.get("discharge_diagnosis") or "",
        main_diagnosis=state.get("main_diagnosis") or "",
    )
    llm = get_llm_factory().get(
        mock_responses={"其他诊断": "[mock]# 其他诊断：\n- 慢性胃炎 K29.500"},
    )
    response = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return {"other_diagnosis": str(content)}
