import pytest

from app import create_app
from app.models import db


@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.test_client() as test_client:
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def make_task(client, **overrides):
    payload = {"title": "Write Dockerfile", "priority": "high"}
    payload.update(overrides)
    return client.post("/api/tasks", json=payload)


def test_health_reports_database_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"]


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Task Tracker" in resp.data


def test_create_task_returns_201(client):
    resp = make_task(client, description="multi-stage build")
    assert resp.status_code == 201
    task = resp.get_json()
    assert task["id"] == 1
    assert task["title"] == "Write Dockerfile"
    assert task["status"] == "todo"
    assert task["priority"] == "high"


def test_create_task_requires_title(client):
    resp = client.post("/api/tasks", json={"title": "   "})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "title is required"


def test_create_task_rejects_invalid_priority(client):
    resp = make_task(client, priority="urgent")
    assert resp.status_code == 400


def test_create_task_rejects_non_json_body(client):
    resp = client.post("/api/tasks", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_and_filter_tasks_by_status(client):
    make_task(client, title="A")
    make_task(client, title="B")
    client.patch("/api/tasks/2", json={"status": "done"})
    all_tasks = client.get("/api/tasks").get_json()
    done = client.get("/api/tasks?status=done").get_json()
    assert all_tasks["count"] == 2
    assert done["count"] == 1
    assert done["tasks"][0]["title"] == "B"


def test_get_missing_task_returns_404(client):
    resp = client.get("/api/tasks/999")
    assert resp.status_code == 404


def test_update_task_status(client):
    make_task(client)
    resp = client.patch("/api/tasks/1", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "in_progress"


def test_update_rejects_invalid_status(client):
    make_task(client)
    resp = client.patch("/api/tasks/1", json={"status": "finished"})
    assert resp.status_code == 400


def test_delete_task(client):
    make_task(client)
    assert client.delete("/api/tasks/1").status_code == 204
    assert client.get("/api/tasks/1").status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not found"


def test_metrics_endpoint_exposes_request_metrics(client):
    make_task(client)
    client.get("/api/tasks")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "http_requests_total" in text
    assert 'endpoint="/api/tasks"' in text
    assert "http_request_duration_seconds_bucket" in text
    assert 'tasks_current{status="todo"} 1.0' in text
