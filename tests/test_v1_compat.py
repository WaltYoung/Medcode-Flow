from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_other_diagnosis_blocking_has_every_node():
    client = _client()
    resp = client.post(
        "/v1/workflows/run",
        headers={
            "Authorization": "Bearer test-key",
            "X-Workflow-Id": "other_diagnosis",
        },
        json={
            "inputs": {
                "discharge_diagnosis": '["慢性胃炎"]',
                "main_diagnosis": "胃窦胃体恶性肿瘤 C16.803",
            },
            "response_mode": "blocking",
            "user": "test-user",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = body["data"]
    assert data["outputs"]["other_diagnosis"]
    titles = [item["title"] for item in data["tracing"]]
    assert titles[0] == "开始"
    assert titles[-1] == "结束"
    assert "将出院诊断列表转换为数组" in titles
    assert "按个提取诊断" in titles
    assert "提取其他诊断" in titles

    fetched = client.get(
        f"/v1/workflows/run/{body['workflow_run_id']}",
        headers={
            "Authorization": "Bearer test-key",
            "X-Workflow-Id": "other_diagnosis",
        },
    )
    assert fetched.status_code == 200
    assert fetched.json()["outputs"]["other_diagnosis"]
    assert fetched.json()["tracing"]


def test_streaming_finished_event_has_outputs():
    client = _client()
    resp = client.post(
        "/v1/workflows/run",
        headers={
            "Authorization": "Bearer test-key",
            "X-Workflow-Id": "other_diagnosis",
        },
        json={
            "inputs": {
                "discharge_diagnosis": '["慢性胃炎"]',
                "main_diagnosis": "胃窦胃体恶性肿瘤 C16.803",
            },
            "response_mode": "streaming",
            "user": "test-user",
        },
    )
    assert resp.status_code == 200, resp.text
    text = resp.text
    assert "event: workflow_finished" in text
    assert '"outputs"' in text
