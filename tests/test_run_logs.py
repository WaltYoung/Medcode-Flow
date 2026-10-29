import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.runtime.run_store import create_run, finish_run


@pytest.fixture
def isolated_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKFLOW_LOG_PATH", str(tmp_path / "runs.sqlite"))
    get_settings.cache_clear()
    import app.runtime.run_store as store

    if store._CONN is not None:
        store._CONN.close()
        store._CONN = None
    yield
    if store._CONN is not None:
        store._CONN.close()
        store._CONN = None
    get_settings.cache_clear()


def test_list_runs_shows_each_call_for_that_workflow(isolated_runs):
    with TestClient(create_app()) as client:
        run_id = f"log-{uuid.uuid4()}"
        create_run(
            run_id=run_id,
            task_id=f"task-{run_id}",
            workflow_id="medical_record_extract",
            user_id="coder-a",
            inputs={"raw_medical_record": "病历正文"},
        )
        finish_run(
            run_id=run_id,
            status="succeeded",
            outputs={"病历概要": "摘要"},
            total_steps=4,
            elapsed_time=1.25,
        )

        denied = client.get("/api/v1/workflows/medical_record_extract/runs")
        assert denied.status_code == 401

        listed = client.get(
            "/api/v1/workflows/medical_record_extract/runs",
            headers={"X-API-Key": "test-key"},
            params={"limit": 20, "offset": 0},
        )
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["total"] == 1
        found = body["items"][0]
        assert found["workflow_run_id"] == run_id
        assert found["status"] == "succeeded"
        assert found["user"] == "coder-a"
        assert found["total_steps"] == 4
        assert "tracing" not in found
        assert "inputs" not in found

        detail = client.get(
            f"/api/v1/workflows/medical_record_extract/runs/{run_id}",
            headers={"X-API-Key": "test-key"},
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["outputs"]["病历概要"] == "摘要"
        assert detail.json()["inputs"]["raw_medical_record"] == "病历正文"

        other = client.get(
            f"/api/v1/workflows/secondary_diagnosis/runs/{run_id}",
            headers={"X-API-Key": "test-key"},
        )
        assert other.status_code == 404

        missing = client.get(
            "/api/v1/workflows/not_a_workflow/runs",
            headers={"X-API-Key": "test-key"},
        )
        assert missing.status_code == 404
