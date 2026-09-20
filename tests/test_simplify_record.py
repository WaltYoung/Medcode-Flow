from app.workflows.medical_record_extract.nodes._simplify_logic import main
from tests.conftest import sample_record_json


def test_simplify_record_extracts_core_fields():
    result = main(sample_record_json())
    assert result["ryrq"] == "2024-01-01"
    assert result["cyrq"] == "2024-01-10"
    assert result["zljg"] == "行化疗一程"
    assert "主诉" in result["ryjl"]
    assert "临时医嘱单" in result["yz"]
    assert result["text"]
    assert result["sample_records"]
