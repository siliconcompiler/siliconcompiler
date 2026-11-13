'''`GET /v1` and `GET /v1/healthz`: what this deployment is, and whether it is up.'''

import logging

import flask

from siliconcompiler.remote.server import config

__all__ = ["blueprint"]


blueprint = flask.Blueprint("meta", __name__)

logger = logging.getLogger("sc-server")


@blueprint.route("/v1", methods=["GET"])
def capabilities():
    response = flask.jsonify(config.capabilities())
    response.headers["Cache-Control"] = "public, max-age=60"
    return response


@blueprint.route("/v1/healthz", methods=["GET"])
def healthz():
    try:
        # A real table: `SELECT 1` never touches the file.
        flask.current_app.config["SC_STORE"].one("SELECT count(*) FROM users")
        status = "pass"
    except Exception as e:                                       # noqa: BLE001
        logger.error(f"health check could not read the store: {e}")
        status = "fail"

    response = flask.jsonify({"status": status})
    response.mimetype = "application/health+json"
    response.status_code = 200 if status == "pass" else 503
    return response
