'''The Flask application: routes, the store and the refusals' shapes.'''

import logging

from pathlib import Path
from typing import List, Optional

import flask

from werkzeug.exceptions import HTTPException

from siliconcompiler.remote.server.errors import OAuthError, ProblemError, problem
from siliconcompiler.remote.server.identity import Identity
from siliconcompiler.remote.server.jobs import Jobs
from siliconcompiler.remote.server.state.store import Store

__all__ = ["create_app"]


logger = logging.getLogger("sc-server")

_HTTP_SLUGS = {404: "not-found", 405: "method-not-allowed"}


def create_app(datadir, cluster: str = "local",
               public_origins: Optional[List[str]] = None) -> flask.Flask:
    '''The server's app, keeping its state under ``datadir``.

    ``public_origins`` are the origins clients address the server by, for a
    DPoP proof's `htu`; none means the request's own URL.
    '''
    from siliconcompiler.remote.server.routes import auth, errorpages, jobs, meta, portal, results

    datadir = Path(datadir).resolve()
    store = Store(datadir / "store.sqlite3")

    app = flask.Flask(__name__)
    app.config.update(SC_DATADIR=datadir, SC_CLUSTER=cluster, SC_STORE=store,
                      SC_IDENTITY=Identity(store), SC_PUBLIC_ORIGINS=public_origins or [],
                      SC_JOBS=Jobs(store, datadir, cluster), SC_PORTAL=portal.Portal())

    for blueprint in (meta.blueprint, auth.blueprint, jobs.blueprint, results.blueprint,
                      portal.blueprint, portal.api, errorpages.blueprint):
        app.register_blueprint(blueprint)

    @app.errorhandler(ProblemError)
    def refused(e):
        return _problem_response(e.body(), e.status, e.headers)

    @app.errorhandler(OAuthError)
    def oauth_refused(e):
        response = flask.jsonify(e.body())
        response.status_code = e.status
        return response

    @app.errorhandler(HTTPException)
    def http_refused(e):
        if e.code >= 500:
            # Untyped, so a client acts on the status: a crash, which Flask has
            # already logged, is not the caller's invalid request.
            return _problem_response({"type": "about:blank", "title": e.name,
                                      "status": e.code}, e.code, {})
        slug = _HTTP_SLUGS.get(e.code, "invalid-request")
        headers = dict(e.get_headers()) if e.code == 405 else {}
        headers.pop("Content-Type", None)
        return _problem_response(problem(slug, status=e.code), e.code, headers)

    @app.after_request
    def uncacheable(response):
        # A cache rule matching /v1/* would serve one caller's answer to another.
        response.headers.setdefault("Cache-Control", "private, no-store")
        return response

    @app.teardown_request
    def release(_):
        store.release()

    return app


def _problem_response(body: dict, status: int, headers: dict):
    from siliconcompiler.remote.server.routes.errorpages import help_link

    response = flask.jsonify(body)
    response.mimetype = "application/problem+json"
    response.status_code = status
    response.headers.update(headers)
    helped = help_link(body["type"])
    if helped:
        response.headers["Link"] = helped
    return response
