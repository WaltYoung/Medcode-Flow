from __future__ import annotations

import json
import re
from typing import Any


def extract_think_and_json(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"think_text": "", "json_content": []}
    think_match = re.search(r"<think>(.*?)</think>", text or "", re.DOTALL)
    if think_match:
        result["think_text"] = think_match.group(1).strip()

    json_patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"(\[\s*\{[\s\S]*?\}\s*\])",
        r"(\[[\s\S]*\])",
    ]
    for pattern in json_patterns:
        match = re.search(pattern, text or "", re.DOTALL)
        if not match:
            continue
        json_str = match.group(1).strip()
        try:
            result["json_content"] = json.loads(json_str)
        except json.JSONDecodeError:
            continue
        break
    return result


def extract_field_by_label(
    text: str,
    label: str,
    *,
    strip_parentheses: bool = True,
) -> str:
    patterns = [
        rf"{re.escape(label)}[：:]\s*([^\n]+)",
        rf"\*\*{re.escape(label)}\*\*[：:]\s*([^\n]+)",
        rf"-\s*{re.escape(label)}[：:]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "")
        if not match:
            continue
        value = match.group(1).strip()
        if strip_parentheses:
            value = re.split(r"[（(]", value)[0].strip()
        return value
    return ""


def parse_discharge_list(cyzd_text: str) -> str:
    """对齐「提取出院诊断列表」：输出 JSON 数组字符串。"""
    cyzd = extract_think_and_json(cyzd_text)["json_content"]
    return json.dumps(cyzd, ensure_ascii=False)


def structure_keywords(zd_text: str) -> dict[str, Any]:
    """对齐「主要诊断关键词结构化」。"""
    zd_list = extract_think_and_json(zd_text)["json_content"]
    if not zd_list:
        zd_list = [zd_text]
    if isinstance(zd_list, dict) and "keywords" in zd_list:
        zd_list = zd_list["keywords"]
    if not isinstance(zd_list, list):
        zd_list = [str(zd_list)]
    return {
        "zd_list": zd_list,
        "zd_list_str": json.dumps(zd_list, ensure_ascii=False),
    }


def merge_keywords(origin_kwargs: list[Any] | None, sg_llm_kwargs: str | None) -> list[Any]:
    """对齐「关键词合并」。"""
    zd_list: list[Any] = list(origin_kwargs or [])
    if sg_llm_kwargs:
        parts = sg_llm_kwargs.split("->")
        last_part = parts[-1].strip() if parts else ""
        if last_part:
            zd_list = [last_part]
    return zd_list


def flatten_kb_contents(knowledges: list[dict[str, Any]]) -> str:
    """对齐「提取知识库」。"""
    result = [{"content": item.get("content")} for item in knowledges]
    return json.dumps(result, ensure_ascii=False)


def parse_json_array(text: str) -> list[Any]:
    parsed = extract_think_and_json(text)["json_content"]
    if isinstance(parsed, list):
        return parsed
    # fallback: bare JSON array
    try:
        data = json.loads((text or "").strip())
        return data if isinstance(data, list) else []
    except Exception:
        return []
