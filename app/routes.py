from flask import Blueprint, Response, current_app, jsonify, render_template, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, text

from .metrics import TASKS_CREATED, TASKS_CURRENT
from .models import PRIORITIES, STATUSES, Task, db

bp = Blueprint("main", __name__)


def _error(message, status=400):
    return jsonify(error=message), status


def _validate(payload, partial=False):
    """Return (clean_data, error_message)."""
    if not isinstance(payload, dict):
        return None, "request body must be a JSON object"
    data = {}
    if "title" in payload or not partial:
        title = str(payload.get("title", "")).strip()
        if not title:
            return None, "title is required"
        if len(title) > 120:
            return None, "title must be at most 120 characters"
        data["title"] = title
    if "description" in payload:
        data["description"] = str(payload["description"]).strip()
    if "priority" in payload:
        if payload["priority"] not in PRIORITIES:
            return None, f"priority must be one of {', '.join(PRIORITIES)}"
        data["priority"] = payload["priority"]
    if "status" in payload:
        if payload["status"] not in STATUSES:
            return None, f"status must be one of {', '.join(STATUSES)}"
        data["status"] = payload["status"]
    return data, None


@bp.get("/")
def index():
    return render_template(
        "index.html",
        version=current_app.config["APP_VERSION"],
        env=current_app.config["APP_ENV"],
    )


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001 - any DB failure means unhealthy
        db.session.rollback()
        database = "unavailable"
    healthy = database == "ok"
    body = {
        "status": "ok" if healthy else "degraded",
        "database": database,
        "version": current_app.config["APP_VERSION"],
        "environment": current_app.config["APP_ENV"],
    }
    return jsonify(body), 200 if healthy else 503


@bp.get("/metrics")
def metrics():
    try:
        rows = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        counts = dict(rows)
        for status in STATUSES:
            TASKS_CURRENT.labels(status=status).set(counts.get(status, 0))
    except Exception:  # noqa: BLE001 - metrics must still be served if the DB is down
        db.session.rollback()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@bp.get("/api/tasks")
def list_tasks():
    query = Task.query.order_by(Task.id)
    status = request.args.get("status")
    if status:
        if status not in STATUSES:
            return _error(f"status must be one of {', '.join(STATUSES)}")
        query = query.filter_by(status=status)
    tasks = [task.to_dict() for task in query.all()]
    return jsonify(count=len(tasks), tasks=tasks)


@bp.post("/api/tasks")
def create_task():
    data, error = _validate(request.get_json(silent=True))
    if error:
        return _error(error)
    task = Task(**data)
    db.session.add(task)
    db.session.commit()
    TASKS_CREATED.inc()
    return jsonify(task.to_dict()), 201


@bp.get("/api/tasks/<int:task_id>")
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _error("task not found", 404)
    return jsonify(task.to_dict())


@bp.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _error("task not found", 404)
    data, error = _validate(request.get_json(silent=True), partial=True)
    if error:
        return _error(error)
    for key, value in data.items():
        setattr(task, key, value)
    db.session.commit()
    return jsonify(task.to_dict())


@bp.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return _error("task not found", 404)
    db.session.delete(task)
    db.session.commit()
    return "", 204
