from __future__ import annotations

import json
import re
from typing import Any


def parse_discharge_diagnosis_list(cyzd: str) -> list[str]:
    """对齐 Dify「将出院诊断列表转换为数组」节点。"""
    raw = (cyzd or "").strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str) and parsed.strip():
        return [parsed.strip()]
    raise ValueError("discharge_diagnosis 必须是 JSON 数组字符串")


def extract_knowledge_for_diagnosis(
    knowledges: list[dict[str, Any]],
    cyzd_name: str,
) -> list[dict[str, str]]:
    """对齐 Dify「提取知识库内容」节点。"""
    icd10_results: list[dict[str, str]] = []
    disease_name = re.escape(cyzd_name)
    pattern = rf"^[^\n]*{disease_name}[^\n]*$"
    for knowledge in knowledges:
        content = knowledge.get("content", "") if isinstance(knowledge, dict) else ""
        matched = re.findall(pattern, content, re.MULTILINE)
        if matched:
            icd10_results.append({"content": "\n".join(matched)})
    return icd10_results
