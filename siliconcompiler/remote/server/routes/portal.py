'''
The portal: a jobs list and a job page, behind a single-use sign-in.

``POST /v1/auth/browser`` hands a client a URL that signs one browser in. The
session is a cookie held in memory, never an API credential, and every decision
goes through the :class:`Jobs` methods the API uses.
'''

import secrets
import tarfile
import threading
import time

from functools import wraps
from types import SimpleNamespace

import flask

from werkzeug.datastructures import MultiDict

from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.jobs import NODE_TERMINAL
from siliconcompiler.remote.server.routes.auth import require_session
from siliconcompiler.remote.server.routes.jobs import origin
from siliconcompiler.remote.server.state.store import iso

__all__ = ["Portal", "api", "blueprint"]


blueprint = flask.Blueprint("portal", __name__, template_folder="../templates")
# Apart from the pages, whose refusals are pages: this one's are problems.
api = flask.Blueprint("portal_api", __name__)

COOKIE = "sc_portal"
# Short and single-use: the URL lands in browser history and maybe an access log.
HANDOVER_SECONDS = 60
SESSION_SECONDS = 43200
# Per log file; a longer log is cut, with a note.
LOG_BYTES = 200_000


class Portal:
    '''Sign-in tokens and browser sessions, in memory: losing them on restart
    costs one ``sc-config remote portal``.'''

    def __init__(self):
        self._handovers = {}
        self._sessions = {}
        self._lock = threading.Lock()

    def offer(self, user_id: str, landing: str):
        '''A single-use token for ``landing``, and when it expires.'''
        token, expires = secrets.token_urlsafe(32), time.time() + HANDOVER_SECONDS
        with self._lock:
            self._sweep()
            self._handovers[token] = (user_id, expires, landing)
        return token, expires

    def redeem(self, token: str):
        '''Spend a token: ``(cookie, landing)``, or None. Popped before it is
        checked, so two requests together cannot both redeem it.'''
        with self._lock:
            self._sweep()
            held = self._handovers.pop(token, None)
            if held is None:
                return None
            cookie = secrets.token_urlsafe(32)
            self._sessions[cookie] = (held[0], time.time() + SESSION_SECONDS,
                                      secrets.token_urlsafe(16))
            return cookie, held[2]

    def lookup(self, cookie):
        '''``(user_id, csrf)`` for a live session, or None.'''
        with self._lock:
            self._sweep()
            held = self._sessions.get(cookie or "")
            return (held[0], held[2]) if held else None

    def end(self, cookie) -> None:
        with self._lock:
            self._sessions.pop(cookie or "", None)

    def _sweep(self) -> None:
        now = time.time()
        for held in (self._handovers, self._sessions):
            for key in [key for key, value in held.items() if value[1] < now]:
                del held[key]


def _portal() -> Portal:
    return flask.current_app.config["SC_PORTAL"]


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _held():
    return _portal().lookup(flask.request.cookies.get(COOKIE))


@blueprint.app_context_processor
def _csrf():
    held = _held() if flask.has_request_context() else None
    return {"csrf": held[1] if held else ""}


def _message(title: str, detail: str, status: int):
    return flask.render_template("message.html", title=title, detail=detail), status


@blueprint.errorhandler(ProblemError)
def _refused(e):
    return _message(e.error.title, e.detail or "", e.status)


def screen(handler):
    '''A page for a signed-in browser; a form post must carry the session's CSRF token.'''
    @wraps(handler)
    def guarded(*args, **kwargs):
        held = _held()
        if held is None:
            return _message("This browser has no session",
                            "Run sc-config remote portal to sign it in.", 401)
        if flask.request.method == "POST" and not secrets.compare_digest(
                flask.request.form.get("csrf", ""), held[1]):
            return _message("That form did not come from here",
                            "Reload the page and try again.", 403)
        return handler(SimpleNamespace(user_id=held[0]), *args, **kwargs)
    return guarded


@api.route("/v1/auth/browser", methods=["POST"])
@require_session
def browser(session):
    '''The sign-in URL for the portal's home or one job's page.'''
    body = flask.request.get_json(silent=True)
    if not isinstance(body, dict) or len(body) > 1 or not set(body) <= {
            "job_id", "terms_id", "artifact_id"}:
        raise ProblemError("invalid-request",
                           detail="the body names at most one of job_id, terms_id, artifact_id")

    landing = flask.url_for("portal.jobs")
    if "job_id" in body:
        job = _jobs().owned(session, str(body["job_id"]))
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="no such job")
        landing = flask.url_for("portal.job", job_id=job["id"])
    elif body:
        raise ProblemError("not-found", detail="this server has no terms or artifact pages")

    token, expires = _portal().offer(session.user_id, landing)
    response = flask.jsonify({
        "url": f"{origin()}{flask.url_for('portal.enter', token=token)}",
        "expires_at": iso(expires)})
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/portal/enter")
def enter():
    '''Spend the token for a session cookie. The landing is the one the token was
    minted with: nothing in this request names where to go.'''
    redeemed = _portal().redeem(flask.request.args.get("token", ""))
    if redeemed is None:
        return _message("That link has been used or has expired",
                        "Run sc-config remote portal again for a new one.", 403)
    response = flask.redirect(redeemed[1])
    response.set_cookie(COOKIE, redeemed[0], max_age=SESSION_SECONDS, httponly=True,
                        samesite="Lax", secure=flask.request.is_secure)
    return response


@blueprint.route("/portal/logout", methods=["POST"])
@screen
def logout(session):
    _portal().end(flask.request.cookies.get(COOKIE))
    response = flask.make_response(
        _message("Signed out", "Run sc-config remote portal to sign in again.", 200))
    response.delete_cookie(COOKIE)
    return response


@blueprint.route("/portal/")
@screen
def jobs(session):
    items, _ = _jobs().listing(session, MultiDict({"limit": "100"}))
    return flask.render_template("jobs.html", jobs=items)


def _logs(session, job_id: str) -> dict:
    '''Each node's log text by ``(step, index)``, from its `logs` artifact.'''
    found = {}
    items, _ = _jobs().artifacts(session, job_id, MultiDict({"kind": "logs", "limit": "200"}))
    for item in items:
        if item["step"] is None:
            continue
        path = _jobs().storage.artifact_dir(job_id) / _jobs().artifact(
            session, job_id, item["id"])["id"]
        text = []
        try:
            with tarfile.open(path) as tar:
                for member in tar:
                    body = tar.extractfile(member).read(LOG_BYTES + 1) if member.isfile() else b""
                    text.append(f"{member.name}\n{body[:LOG_BYTES].decode(errors='replace')}"
                                f"{'... cut' if len(body) > LOG_BYTES else ''}")
        except (OSError, tarfile.TarError):
            continue
        found[item["step"], item["index"]] = "\n".join(text)
    return found


@blueprint.route("/portal/jobs/<job_id>")
@screen
def job(session, job_id):
    detail = _jobs().get(session, job_id)
    if detail["deleted_at"]:
        raise ProblemError("not-found", detail="no such job")
    logs = _logs(session, job_id) if any(
        node["state"] in NODE_TERMINAL for node in detail["nodes"]) else {}
    reasons = [t["reason"] for t in detail["transitions"] if t.get("reason")]
    return flask.render_template("job.html", job=detail, logs=logs, reasons=reasons)


@blueprint.route("/portal/jobs/<job_id>/cancel", methods=["POST"])
@screen
def cancel(session, job_id):
    _jobs().cancel(session, job_id, None)
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/delete", methods=["POST"])
@screen
def delete(session, job_id):
    _jobs().delete(session, job_id)
    return flask.redirect(flask.url_for("portal.jobs"))
