"""Task Tracker: a small Flask web application used to practise DevOps workflows.

The application factory below wires together configuration, the database,
structured (JSON) logging and Prometheus request metrics.
"""
import logging
import os
import time

from flask import Flask, g, jsonify, request
from sqlalchemy.exc import OperationalError

from .logging_config import configure_logging
from .metrics import REQUEST_COUNT, REQUEST_LATENCY, REQUESTS_IN_PROGRESS, BUILD_INFO
from .models import db

__version__ = "1.0.0"

log = logging.getLogger("task_tracker")
access_log = logging.getLogger("task_tracker.access")


def _init_database(app, attempts=10, delay=2.0):
    """Create tables, retrying while the database container is still starting."""
    for attempt in range(1, attempts + 1):
        try:
            with app.app_context():
                db.create_all()
            log.info("database ready", extra={"attempt": attempt})
            return
        except OperationalError as exc:
            if attempt == attempts:
                raise
            log.warning(
                "database not ready, retrying",
                extra={"attempt": attempt, "error": str(exc.orig)},
            )
            time.sleep(delay)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///task_tracker.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        APP_ENV=os.environ.get("APP_ENV", "development"),
        APP_VERSION=__version__,
    )
    app.json.sort_keys = False
    if test_config:
        app.config.update(test_config)

    configure_logging(os.environ.get("LOG_LEVEL", "INFO"), os.environ.get("LOG_FILE"))
    BUILD_INFO.labels(version=__version__, env=app.config["APP_ENV"]).set(1)

    db.init_app(app)
    _init_database(app)

    from .routes import bp

    app.register_blueprint(bp)

    @app.before_request
    def _start_timer():
        g.start_time = time.perf_counter()
        REQUESTS_IN_PROGRESS.inc()

    @app.after_request
    def _record_request(response):
        duration = time.perf_counter() - g.get("start_time", time.perf_counter())
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
        if endpoint != "/metrics":
            access_log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "remote_addr": request.remote_addr,
                },
            )
        return response

    @app.teardown_request
    def _finish(_exc):
        REQUESTS_IN_PROGRESS.dec()

    @app.errorhandler(404)
    def _not_found(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def _method_not_allowed(_err):
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(500)
    def _server_error(_err):
        log.exception("unhandled error")
        return jsonify(error="internal server error"), 500

    log.info("application started", extra={"version": __version__, "env": app.config["APP_ENV"]})
    return app
