'''
The portal: six screens over the same decisions the API makes.

🔴 **Every authorization decision here goes through the code the API handlers
call** -- ``JobService.owned``, ``accounts.owned_device``, and the rest. Not
because duplication is untidy, but because a portal query that forgets
``WHERE user_id =`` answers ``200`` and looks correct, and this project has
shipped exactly that defect once. There is one place to forget it, and it is
shared.

⚠️ **The portal does not call its own API over HTTP.** A browser holds no device
key, and an HTTP client that could reach ``/v1`` would need a credential that is
not key-bound -- the one shape the auth model exists to avoid. So it reads
through the shared layer instead, and every link it hands the browser for bytes
is a *signed* storage URL, whose signature is the whole credential.

🔴 **A portal session is a cookie and never becomes an API credential.** It
mints no access token and carries no DPoP binding. A path from one to the other
would be the shortest way around the key pinning, so there is none.
'''

import logging
import secrets
import threading
import time

from typing import Optional

import flask

from siliconcompiler.remote.server import accounts, images
from siliconcompiler.remote.server.auth import SCOPES, Session
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.storage import DOWNLOAD_SECONDS

__all__ = ["blueprint", "Sessions"]


logger = logging.getLogger("sc-server")

blueprint = flask.Blueprint("portal", __name__, template_folder="templates")

COOKIE = "sc_portal"

# Seconds to a minute, because the URL is handed to a browser on the same
# machine and there is no legitimate slow path. It reaches the browser's
# history and possibly an access log, so spending it on arrival is what makes
# both worthless.
HANDOVER_SECONDS = 60

# A working session. Not the API's twelve days: a browser session is a
# convenience and re-obtaining one costs a single command.
SESSION_SECONDS = 43200


class Sessions:
    '''Browser sessions, in memory and nowhere else.

    🔴 Deliberately not a table. crucible's portal session is its identity
    provider's and is in none of the 41 either -- session state is not what
    this schema is for. A handover token that lives under a minute has no
    business surviving a restart, and a browser session that does not survive
    one is a person running ``sc-remote -portal`` again.
    '''

    def __init__(self):
        self._handovers = {}
        self._sessions = {}
        self._lock = threading.Lock()

    def offer(self, user_id: str) -> str:
        '''Mint a single-use token for one browser.'''
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._expire()
            self._handovers[token] = (user_id, time.time() + HANDOVER_SECONDS)
        return token

    def redeem(self, token: str):
        '''Spend a handover token. Returns ``(cookie, csrf)`` or None.

        🔴 Removed before it is checked, so a token cannot be redeemed twice
        even by two requests arriving together.
        '''
        with self._lock:
            self._expire()
            held = self._handovers.pop(token, None)
            if held is None:
                return None

            user_id, expires = held
            if expires < time.time():
                return None

            cookie = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(16)
            self._sessions[cookie] = (user_id, time.time() + SESSION_SECONDS, csrf)
            return cookie, csrf

    def lookup(self, cookie: Optional[str]):
        '''``(user_id, csrf)`` for a live session, or None.'''
        if not cookie:
            return None
        with self._lock:
            self._expire()
            held = self._sessions.get(cookie)
            if held is None:
                return None
            user_id, expires, csrf = held
            if expires < time.time():
                del self._sessions[cookie]
                return None
            return user_id, csrf

    def end(self, cookie: Optional[str]) -> None:
        with self._lock:
            self._sessions.pop(cookie or "", None)

    def _expire(self) -> None:
        cutoff = time.time()
        for token, (_, expires) in list(self._handovers.items()):
            if expires < cutoff:
                del self._handovers[token]
        for cookie, (_, expires, _csrf) in list(self._sessions.items()):
            if expires < cutoff:
                del self._sessions[cookie]


######################################################################
# Getting in
######################################################################

def _sessions() -> Sessions:
    return flask.current_app.config["SC_PORTAL"]


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _store():
    return flask.current_app.config["SC_STORE"]


def caller():
    '''The signed-in user, as the SAME Session object the API builds.

    🔴 The point of returning the API's own type: every service call below then
    takes the identical argument an API handler would pass, so there is no
    second notion of who is asking.

    ⚠️ It carries the full scope set rather than a narrowed one, and that is
    honest rather than lax -- the portal offers exactly what the API offers this
    person. What it is NOT is a credential: nothing here can be presented to
    ``/v1``.
    '''
    held = _sessions().lookup(flask.request.cookies.get(COOKIE))
    if held is None:
        return None

    user_id, _csrf = held
    return Session(user_id=user_id, scope=" ".join(SCOPES),
                   family_id=None, device_id=None, jkt=None)


def screen(handler):
    '''A page that needs a session, rendering refusals as pages.'''
    from functools import wraps

    @wraps(handler)
    def guarded(*args, **kwargs):
        session = caller()
        if session is None:
            return flask.render_template("signin.html"), 401

        if flask.request.method == "POST" and not _csrf_ok():
            # A form posted from somewhere else. SameSite=Strict already
            # refuses the cookie on a cross-site POST; this is the half that
            # does not depend on the browser being recent.
            return flask.render_template(
                "problem.html", title="That form did not come from here",
                detail="Reload the page and try again."), 403

        try:
            return handler(session, *args, **kwargs)
        except ProblemError as refusal:
            return flask.render_template(
                "problem.html", title=refusal.error.title,
                detail=refusal.detail or ""), refusal.status

    return guarded


def _csrf_ok() -> bool:
    held = _sessions().lookup(flask.request.cookies.get(COOKIE))
    if held is None:
        return False
    return secrets.compare_digest(flask.request.form.get("csrf", ""), held[1])


@blueprint.app_template_filter("runtime")
def _runtime(node) -> str:
    '''How long a node took, or how long it has been going.

    Computed here rather than in the template because a template that can do
    arithmetic on timestamps is a template that will.
    '''
    started, finished = node.get("started_at"), node.get("finished_at")
    if not started:
        return "\u2014"

    end = _epoch(finished) if finished else time.time()
    begin = _epoch(started)
    if end is None or begin is None:
        return "\u2014"

    seconds = max(0, int(end - begin))
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def _epoch(stamp: Optional[str]) -> Optional[float]:
    from datetime import datetime, timezone

    if not stamp:
        return None
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


@blueprint.app_context_processor
def _csrf_for_templates():
    held = _sessions().lookup(flask.request.cookies.get(COOKIE)) \
        if flask.has_request_context() else None
    return {"csrf": held[1] if held else ""}


@blueprint.route("/portal/session", methods=["POST"])
def offer_session():
    '''The CLI asks for a browser session, proving it holds its key.

    Outside ``/v1`` because ``/v1`` is exactly the contract's twenty-two
    endpoints and this is not one of them -- the same reason the signed upload
    ``PUT`` lives outside it.
    '''
    from siliconcompiler.remote.server.routes.auth import current_session

    session = current_session()
    session.require("profile:read")

    token = _sessions().offer(session.user_id)
    url = flask.url_for("portal.enter", token=token, _external=True)

    response = flask.jsonify({"url": url, "expires_in": HANDOVER_SECONDS})
    response.headers["Cache-Control"] = "private, no-store"
    return response


@blueprint.route("/portal/enter")
def enter():
    '''Exchange the token for a cookie, and destroy the token.'''
    redeemed = _sessions().redeem(flask.request.args.get("token", ""))
    if redeemed is None:
        return flask.render_template(
            "problem.html", title="That link has been used or has expired",
            detail="Run sc-remote -portal again to get a new one."), 403

    cookie, _csrf = redeemed
    response = flask.redirect(flask.url_for("portal.jobs"))
    response.set_cookie(
        COOKIE, cookie, max_age=SESSION_SECONDS, httponly=True,
        samesite="Strict",
        # Only over https where the request arrived over https: this profile is
        # permitted plaintext, and a Secure cookie on a plaintext deployment is
        # a session that silently never arrives.
        secure=flask.request.is_secure)
    return response


@blueprint.route("/portal/logout", methods=["POST"])
def logout():
    _sessions().end(flask.request.cookies.get(COOKIE))
    response = flask.redirect(flask.url_for("portal.jobs"))
    response.delete_cookie(COOKIE)
    return response


######################################################################
# Jobs
######################################################################

@blueprint.route("/portal/", methods=["GET"])
@screen
def jobs(session):
    args = dict(flask.request.args)
    args.setdefault("limit", "50")
    items, _cursor = _jobs().listing(session, args)
    return flask.render_template("jobs.html", jobs=items,
                                 state=flask.request.args.get("state", ""))


@blueprint.route("/portal/jobs/<job_id>", methods=["GET"])
@screen
def job(session, job_id):
    detail = _jobs().get(session, job_id)
    edges = _store().all(
        "SELECT * FROM job_node_edges WHERE job_id = ?", (job_id,))
    history = _store().all(
        "SELECT * FROM job_state_transitions WHERE job_id = ? "
        "ORDER BY occurred_at", (job_id,))
    placements = _placements(job_id)

    return flask.render_template("job.html", job=detail, edges=edges,
                                 history=history, placements=placements)


def _placements(job_id):
    '''Which image and which scheduler job each node ran in.

    ⚠️ Neither is published on the wire -- a registry path and a scheduler id
    are deployment detail -- and the contract's answer to *where does a person
    see them* is this screen. It is the reason both columns are written.
    '''
    refs = {row["id"]: row["registry_ref"]
            for row in _store().all("SELECT id, registry_ref FROM images")}

    return {(row["step"], row["index"]):
            (refs.get(row["image_id"]), row["scheduler_job_id"])
            for row in _store().all(
                'SELECT step, "index", image_id, scheduler_job_id '
                "FROM job_nodes WHERE job_id = ?", (job_id,))}


@blueprint.route("/portal/jobs/<job_id>/cancel", methods=["POST"])
@screen
def cancel(session, job_id):
    _jobs().cancel(session, job_id, flask.request.form.get("reason") or None)
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/delete", methods=["POST"])
@screen
def delete(session, job_id):
    _jobs().delete(session, job_id)
    return flask.redirect(flask.url_for("portal.jobs"))


######################################################################
# Artifacts and logs
######################################################################

@blueprint.route("/portal/jobs/<job_id>/artifacts", methods=["GET"])
@screen
def artifacts(session, job_id):
    detail = _jobs().get(session, job_id)
    items = _jobs().artifacts(session, job_id, flask.request.args)
    return flask.render_template("artifacts.html", job=detail, artifacts=items)


@blueprint.route("/portal/jobs/<job_id>/artifacts/<artifact_id>", methods=["GET"])
@screen
def fetch(session, job_id, artifact_id):
    '''Hand the browser a signed URL for the bytes.

    🔴 The same row and the same refusals the API answers with, and then the
    same signature: a browser can follow a signed storage URL because the
    signature is the credential. Nothing here invents a way for a cookie to
    authorise a download.
    '''
    row = _jobs().artifact(session, job_id, artifact_id)
    storage = flask.current_app.config["SC_STORAGE"]

    expires = int(time.time()) + DOWNLOAD_SECONDS
    signature = storage.sign_download(row["id"], expires)

    return flask.redirect(flask.url_for(
        "artifacts.download", job_id=job_id, artifact_id=row["id"],
        expires=expires, sig=signature))


@blueprint.route("/portal/jobs/<job_id>/logs/<step>/<index>", methods=["GET"])
@screen
def log(session, job_id, step, index):
    '''One node's log: the archived bytes, or the live tail as it is written.'''
    detail = _jobs().get(session, job_id)
    kind, target = _jobs().node_log(session, job_id, step, index)

    text, stream = "", None
    if kind == "artifact":
        storage = flask.current_app.config["SC_STORAGE"]
        path = storage.artifact_path(target["storage_key"])
        try:
            with open(path, errors="replace") as handle:
                text = handle.read()
        except OSError as e:
            text = f"(the archived log could not be read: {e})"
    else:
        # Running. The browser follows the same signed stream URL the CLI does,
        # which is what makes this a viewer for the API rather than a second
        # implementation of tailing.
        storage = flask.current_app.config["SC_STORAGE"]
        expires = int(time.time()) + flask.current_app.config[
            "SC_CONFIG"].limits["max_log_stream_seconds"]
        stream = flask.url_for(
            "artifacts.tail", job_id=job_id, step=step, index=index,
            expires=expires,
            sig=storage.sign_stream(job_id, step, index, expires))

    return flask.render_template("log.html", job=detail, step=step, index=index,
                                 text=text, stream=stream)


######################################################################
# Devices and account
######################################################################

@blueprint.route("/portal/devices", methods=["GET"])
@screen
def devices(session):
    rows = accounts.devices_for(_store(), session)
    return flask.render_template("devices.html", devices=rows)


@blueprint.route("/portal/devices/<device_id>/revoke", methods=["POST"])
@screen
def revoke(session, device_id):
    device = accounts.owned_device(_store(), session, device_id)
    flask.current_app.config["SC_ISSUER"].revoke_device(
        device["id"], session.user_id)
    return flask.redirect(flask.url_for("portal.devices"))


@blueprint.route("/portal/account", methods=["GET"])
@screen
def account(session):
    config = flask.current_app.config["SC_CONFIG"]
    return flask.render_template(
        "account.html",
        user=accounts.user(_store(), session.user_id),
        limits=accounts.account_limits(config),
        usage=accounts.usage(_store(), session.user_id),
        assurance=config["identity_assurance"],
        containers=config["containers"])


######################################################################
# Images and software
######################################################################

@blueprint.route("/portal/images", methods=["GET"])
@screen
def registry(session):
    config = flask.current_app.config["SC_CONFIG"]
    return flask.render_template(
        "images.html", catalogue=images.catalogue(_store(), include_retired=True),
        containers=config["containers"],
        staged={image["digest"]: images.is_staged(
            images.bundle_path(_jobs().bundles_root(), image["digest"]))
            for image in images.live_images(_store())})


@blueprint.route("/portal/images/software", methods=["POST"])
@screen
def add_software(session):
    name = (flask.request.form.get("name") or "").strip()
    version = (flask.request.form.get("version") or "").strip()
    if not name:
        raise ProblemError("invalid-request", detail="a distribution name is required")

    images.register_software(_store(), name,
                             flask.request.form.get("display") or name,
                             session.user_id)
    if version:
        images.register_version(_store(), name, version, session.user_id,
                                preference=_int(flask.request.form.get("preference")))

    return flask.redirect(flask.url_for("portal.registry"))


@blueprint.route("/portal/images/register", methods=["POST"])
@screen
def register_image(session):
    '''🔴 The most dangerous write this server has: it chooses what code runs
    on the cluster.

    Which is why it takes a person and records them. There is no CI path here
    -- ``registered_via`` is crucible's -- so every image on this deployment
    has somebody's id on it.
    '''
    ref = (flask.request.form.get("ref") or "").strip()
    digest = (flask.request.form.get("digest") or "").strip()
    contains = [line.strip() for line
                in (flask.request.form.get("contains") or "").splitlines()
                if line.strip()]

    pairs = []
    for entry in contains:
        name, sep, version = entry.partition("==")
        if not sep:
            raise ProblemError("invalid-request",
                               detail=f"{entry!r} is not name==version")
        pairs.append((name.strip(), version.strip()))

    try:
        image_id = images.register_image(
            _store(), ref, digest, pairs, session.user_id,
            note=flask.request.form.get("note") or None)
    except ValueError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    if flask.request.form.get("stage"):
        try:
            images.stage_bundle(
                _jobs().bundles_root(), images.pinned_ref(ref, digest), digest,
                mounts=_jobs().container_mounts())
        except Exception as e:                                   # noqa: BLE001
            raise ProblemError(
                "unsatisfiable-request", resource_kind="library", resource=ref,
                detail=f"registered, but the bundle could not be unpacked: {e}"
            ) from None
        logger.info(f"staged a bundle for {image_id}")

    return flask.redirect(flask.url_for("portal.registry"))


@blueprint.route("/portal/images/<image_id>/retire", methods=["POST"])
@screen
def retire_image(session, image_id):
    images.retire_image(_store(), image_id, session.user_id)
    return flask.redirect(flask.url_for("portal.registry"))


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
