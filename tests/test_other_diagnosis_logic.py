from app.workflows.other_diagnosis.nodes.logic import (
    extract_knowledge_for_diagnosis,
    parse_discharge_diagnosis_list,
)


def test_parse_discharge_diagnosis_list():
    assert parse_discharge_diagnosis_list(
        '["急性心肌梗死","慢性胃炎"]'
    ) == ["急性心肌梗死", "慢性胃炎"]


def test_extract_knowledge_for_diagnosis_filters_lines():
    knowledges = [
        {"content": "急性心肌梗死(I21.900)\n慢性胃炎(K29.500)"},
        {"content": "高血压病3级（极高危）(I10.x00x032)"},
    ]
    got = extract_knowledge_for_diagnosis(knowledges, "慢性胃炎")
    assert got == [{"content": "慢性胃炎(K29.500)"}]
