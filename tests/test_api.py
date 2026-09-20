from fastapi.testclient import TestClient

from app.main import create_app
from app.runtime.tasks import MemoryTaskStore
from app.runtime.worker import process_one
from tests.conftest import sample_record_json


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_and_list_workflows():
    client = _client()
    assert client.get("/api/v1/health").json()["status"] == "ok"
    resp = client.get("/api/v1/workflows", headers={"X-API-Key": "test-key"})
    assert resp.status_code == 200
    ids = [item["workflow_id"] for item in resp.json()]
    assert "medical_record_extract" in ids


def test_invoke_requires_api_key():
    client = _client()
    resp = client.post(
        "/api/v1/workflows/medical_record_extract/invoke",
        json={"raw_medical_record": sample_record_json()},
    )
    assert resp.status_code == 401


def test_sync_invoke():
    client = _client()
    resp = client.post(
        "/api/v1/workflows/medical_record_extract/invoke",
        headers={"X-API-Key": "test-key"},
        json={"raw_medical_record": sample_record_json()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["medical_summary"]
    assert "diagnosis_list" in body["result"]


def test_async_invoke_and_poll(monkeypatch):
    store = MemoryTaskStore()
    monkeypatch.setattr("app.api.v1.workflows.task_store", store)
    monkeypatch.setattr("app.runtime.worker.task_store", store)
    monkeypatch.setattr("app.runtime.tasks.task_store", store)

    client = _client()
    resp = client.post(
        "/api/v1/workflows/medical_record_extract/invoke-async",
        headers={"X-API-Key": "test-key"},
        json={"raw_medical_record": sample_record_json()},
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    process_one(task_id)
    polled = client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"X-API-Key": "test-key"},
    )
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["result"]["result"]["medical_summary"]
