"""图节点 id 到日志标题。"""

from __future__ import annotations

NODE_TITLES: dict[str, dict[str, str]] = {
    "medical_record_extract": {
        "current_time": "当前时间",
        "simplify_record": "拆分病历材料",
        "init": "病历概要",
        "has_history_diagnosis": "是否存在历史确诊",
        "is_first_antitumor": "是否首次抗肿瘤治疗",
        "abandon_or_skip": "是否放弃原治疗计划",
        "tumor_info": "肿瘤原文",
        "malignant_location": "恶性病灶位置",
        "sublocation": "亚部位",
        "location_consistency": "位置是否一致",
        "distribution_type": "分布类型",
        "diagnosis_list": "诊断清单",
        "treatment_methods": "治疗方式",
    },
    "secondary_diagnosis": {
        "select_main": "选定主要诊断",
        "keyword_pipeline": "抽取检索词",
        "tumor_site_and_merge": "识别肿瘤器官",
        "kb_iterate": "调用肿瘤库",
        "normalize_main": "规范主要诊断",
        "extract_discharge": "抽出出院诊断",
        "parse_discharge": "解析出院诊断",
        "call_other_diagnosis": "提取其他诊断",
    },
    "other_diagnosis": {
        "parse_discharge_list": "将出院诊断列表转换为数组",
        "iterate_knowledge": "按个提取诊断",
        "extract_other_diagnosis": "提取其他诊断",
    },
}


def node_title(workflow_id: str, node_id: str) -> str:
    return NODE_TITLES.get(workflow_id, {}).get(node_id, node_id)
