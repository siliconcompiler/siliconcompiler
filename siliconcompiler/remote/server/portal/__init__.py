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

import json
import logging
import posixpath
import secrets
import tarfile
import threading
import time

from typing import Optional

import flask
import markupsafe

from siliconcompiler.remote import units
from siliconcompiler.remote.server import accounts, images
from siliconcompiler.remote.server.artifacts import fetchable
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

# The page somebody was turned away from, kept just long enough to run one
# command and come back. Separate from the session cookie because it is not a
# credential: it is a breadcrumb, and it is treated as untrusted input.
NEXT_COOKIE = "sc_portal_next"
HANDOVER_NEXT_SECONDS = 900

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

    def offer(self, user_id: str, landing=None) -> str:
        """Mint a single-use token for one browser.

        `landing` is where to send it once the cookie is set -- already
        validated by the caller, because this class stores what it is given.
        """
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._expire()
            self._handovers[token] = (user_id, time.time() + HANDOVER_SECONDS,
                                      landing)
        return token

    def redeem(self, token: str):
        '''Spend a handover token. Returns ``(cookie, csrf, landing)`` or None.

        🔴 Removed before it is checked, so a token cannot be redeemed twice
        even by two requests arriving together.
        '''
        with self._lock:
            self._expire()
            held = self._handovers.pop(token, None)
            if held is None:
                return None

            user_id, expires, landing = held
            if expires < time.time():
                return None

            cookie = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(16)
            self._sessions[cookie] = (user_id, time.time() + SESSION_SECONDS, csrf)
            return cookie, csrf, landing

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
        for token, (_, expires, _landing) in list(self._handovers.items()):
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
            # 🔴 Remember where they were going. A `web_url` printed by the CLI
            # is a link somebody clicks cold, and without this the handover
            # always lands on the jobs list -- so the answer to "here is your
            # job" was "here is a list, go and find it". It goes in a cookie
            # because the CLI mints the handover and never sees this request.
            page = flask.make_response(flask.render_template("signin.html"), 401)
            if flask.request.method == "GET":
                page.set_cookie(
                    NEXT_COOKIE, flask.request.path,
                    max_age=HANDOVER_NEXT_SECONDS, httponly=True,
                    samesite="Strict", secure=flask.request.is_secure)
            return page

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

    return units.duration(max(0, int(end - begin)))


@blueprint.app_context_processor
def _limits():
    """What the templates need to not offer a link this will refuse."""
    return {"browse_limit": MAX_BROWSE_BYTES}


@blueprint.app_template_filter("size")
def _size(num_bytes) -> str:
    """Bytes as a person reads them. Shared with the CLI -- see remote.units."""
    return units.size(num_bytes)


@blueprint.app_template_filter("duration")
def _duration(seconds) -> str:
    return units.duration(seconds)


@blueprint.app_template_filter("when")
def _when(timestamp) -> markupsafe.Markup:
    '''One instant, as the reader's own clock shows it.

    🔴 The server cannot know the browser's timezone, and it must not guess:
    the container's clock is UTC, the person reading is not, and a bare
    `2026-09-24 01:34` with no zone is the worst of the three answers because
    it looks right.

    So the instant goes out as UTC in a `<time datetime>` -- which is what it
    is -- and ten lines of inline script at the bottom of every page rewrite
    the text to local. ⚠️ **That spends half of "server-rendered Python, no
    JavaScript build": there is still no build, no dependency and no
    toolchain, and the page is correct and readable with scripting off**,
    which is the half that was actually load-bearing.
    '''
    if not timestamp:
        return markupsafe.Markup('<span class="muted">\u2014</span>')

    text = str(timestamp)
    # "2026-09-24T01:34:12.218Z" -> "2026-09-24 01:34:12 UTC", which is what a
    # reader sees if the script never runs.
    readable = text[:19].replace("T", " ") + " UTC"
    return markupsafe.Markup(
        f'<time datetime="{markupsafe.escape(text)}" '
        f'class="ts">{markupsafe.escape(readable)}</time>')


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

    # 🔴 Where to land, validated exactly as the cookie is -- it arrives from a
    # client, and a redirect that follows caller-supplied input is an open
    # redirect whichever door it came through. The client sends the job's page
    # so that one URL both authenticates and arrives somewhere useful.
    body = flask.request.get_json(silent=True) or {}
    token = _sessions().offer(session.user_id, _safe_path(body.get("next")))
    url = flask.url_for("portal.enter", token=token, _external=True)

    response = flask.jsonify({"url": url, "expires_in": HANDOVER_SECONDS})
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _safe_path(path):
    """A local portal path, or nothing.

    🔴 Two characters decide it: it must begin `/portal/`, and must not begin
    `//`, which a browser reads as a scheme-relative host. This is the one
    function that says yes to a redirect target, so both doors -- the cookie
    and the handover -- come through it.
    """
    if isinstance(path, str) and path.startswith("/portal/") \
            and not path.startswith("//"):
        return path
    return None


def _wanted():
    """Where the browser was going when it was turned away.

    🔴 A local portal path or nothing. Anything can set a cookie on this
    origin, and a redirect that follows one is an open redirect -- the classic
    phishing primitive, made worse here because the person has just been told
    this link is the trustworthy way in. Two checks decide it: it must begin
    `/portal/`, and must not begin `//`, which a browser reads as a
    scheme-relative host.
    """
    return _safe_path(flask.request.cookies.get(NEXT_COOKIE))


@blueprint.route("/portal/enter")
def enter():
    '''Exchange the token for a cookie, and destroy the token.'''
    redeemed = _sessions().redeem(flask.request.args.get("token", ""))
    if redeemed is None:
        return flask.render_template(
            "problem.html", title="That link has been used or has expired",
            detail="Run sc-remote -portal again to get a new one."), 403

    cookie, _csrf, landing = redeemed

    # 🔴 The handover's own destination first. The CLI knew which job it had
    # just submitted; the cookie only knows where this browser was turned away
    # from, which is nothing at all when the browser is being opened for the
    # first time.
    response = flask.redirect(
        landing or _wanted() or flask.url_for("portal.jobs"))
    response.delete_cookie(NEXT_COOKIE, samesite="Strict")
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

    # 🔴 `archived` is the one filter here whose default is not *everything*:
    # absent means the unarchived list, `true` means only the archived ones,
    # and there is deliberately no value meaning both -- a mixed list is the
    # state archiving exists to end. So the screen needs a way back, or
    # archiving a job hides it with no way to find it again.
    return flask.render_template(
        "jobs.html", jobs=items,
        state=flask.request.args.get("state", ""),
        archived=flask.request.args.get("archived") == "true")


@blueprint.route("/portal/jobs/<job_id>", methods=["GET"])
@screen
def job(session, job_id):
    detail = _jobs().get(session, job_id)
    edges = _store().all(
        "SELECT * FROM job_node_edges WHERE job_id = ?", (job_id,))
    history = _store().all(
        "SELECT * FROM job_state_transitions WHERE job_id = ? "
        "ORDER BY occurred_at", (job_id,))

    # 🔴 Returns (items, cursor). Handing the tuple straight to a template
    # renders a page with nothing on it and no error, which is how this shipped
    # once already.
    items = _all_artifacts(session, job_id)

    per_node = {}
    for item in items:
        per_node.setdefault((item["step"], item["index"]), []).append(item)

    # 🔴 The same order as the picture beside it, which is the order the run
    # reaches them -- not the alphabetical one the API lists.
    detail["nodes"] = running_order(detail, edges)

    return flask.render_template(
        "job.html", job=detail, edges=edges, history=history,
        placements=_jobs().node_placements(session, job_id), per_node=per_node,
        job_level=per_node.get((None, None), []),
        # The run's own log, so the job page can offer it as a button rather
        # than as a row three tables down. It is the first thing anybody wants
        # on a job that failed outside a node.
        job_log=next((item for item in per_node.get((None, None), [])
                      if item["kind"] == "logs" and item["fetchable"]), None),
        graph=_graph(detail, edges))


# One box, and the numbers are the whole layout engine.
#
# ⚠️ Laid out DOWNWARDS, not across. A flow is deep and narrow -- asicflow is
# twenty-three nodes in about as many stages -- so left-to-right made a picture
# wider than any page and one box tall, which is a scrollbar rather than a
# diagram. Downwards it is narrow enough to sit beside the tables.
_BOX_W, _BOX_H, _GAP_X, _GAP_Y, _PAD = 132, 28, 14, 22, 12


def _depths(nodes, edges):
    """How far into the run each node is: the longest path to it.

    🔴 For a flowgraph that IS the order the work happens in, which is why the
    same number lays out the picture and sorts the table beside it. Two views
    of one run disagreeing about what comes first is worse than either ordering
    on its own.
    """
    incoming = {node: [] for node in nodes}
    for edge in edges:
        target = (edge["to_step"], edge["to_index"])
        source = (edge["from_step"], edge["from_index"])
        if target in incoming and source in incoming:
            incoming[target].append(source)

    depth = {}

    def _of(node, seen=()):
        if node in depth:
            return depth[node]
        if node in seen:
            # A cycle cannot happen in a flowgraph, and a layout routine is not
            # the place to find out that one did.
            return 0
        found = max((_of(parent, seen + (node,)) + 1
                     for parent in incoming[node]), default=0)
        depth[node] = found
        return found

    for node in nodes:
        _of(node)
    return depth


def running_order(job, edges):
    """The job's nodes, in the order the run reaches them.

    ⚠️ The API lists nodes by name, which puts `elaborate` in the MIDDLE of a
    23-node asicflow, between `cts` and `floorplan`. That is a fine ordering
    for a listing a client will sort itself and the wrong one for a table
    somebody reads top to bottom while the run is going.

    Ties break on the name, so two runs of the same flow render identically and
    a reload never reshuffles the rows.
    """
    nodes = [(node["step"], node["index"]) for node in job.get("nodes") or []]
    depth = _depths(nodes, edges)

    return sorted(job.get("nodes") or [],
                  key=lambda node: (depth.get((node["step"], node["index"]), 0),
                                    node["step"], node["index"]))


def _graph(job, edges):
    '''The flowgraph, as inline SVG.

    🔴 Drawn on the server, in about forty lines, because the alternative is a
    JavaScript graph library -- and SiliconCompiler ships as a pip wheel, so a
    node toolchain in the release pipeline would be paid by every release for
    one picture.

    A layered layout: a node's ROW is the longest path to it, which for a
    flowgraph is exactly the order the work happens in, read top to bottom.
    Columns inside a row are the order the nodes were listed, so two runs of
    the same flow draw the same picture.
    '''
    nodes = [(node["step"], node["index"]) for node in job.get("nodes") or []]
    if not nodes:
        return None

    states = {(node["step"], node["index"]): node["state"]
              for node in job["nodes"]}
    depth = _depths(nodes, edges)

    columns = {}
    for node in nodes:
        columns.setdefault(depth[node], []).append(node)

    widest = max(len(members) for members in columns.values())

    place = {}
    for depth_of, members in columns.items():
        # Centred, so a fan-out reads as one and a single-node stage sits under
        # the stage above it rather than hard against the left edge.
        offset = (widest - len(members)) * (_BOX_W + _GAP_X) / 2
        for across, node in enumerate(members):
            place[node] = (_PAD + offset + across * (_BOX_W + _GAP_X),
                           _PAD + depth_of * (_BOX_H + _GAP_Y))

    width = _PAD * 2 + widest * (_BOX_W + _GAP_X) - _GAP_X
    height = _PAD * 2 + (max(columns) + 1) * (_BOX_H + _GAP_Y) - _GAP_Y

    out = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           'class="flow" xmlns="http://www.w3.org/2000/svg">']

    for edge in edges:
        source = (edge["from_step"], edge["from_index"])
        target = (edge["to_step"], edge["to_index"])
        if source not in place or target not in place:
            continue
        x1, y1 = place[source]
        x2, y2 = place[target]
        x1, y1 = x1 + _BOX_W / 2, y1 + _BOX_H
        x2 = x2 + _BOX_W / 2
        mid = (y1 + y2) / 2
        out.append(f'<path d="M{x1},{y1} C{x1},{mid} {x2},{mid} {x2},{y2}" '
                   'class="wire" fill="none"/>')

    for node, (x, y) in place.items():
        step, index = node
        out.append(
            f'<g class="node {states.get(node, "pending")}">'
            f'<rect x="{x}" y="{y}" width="{_BOX_W}" height="{_BOX_H}" rx="5"/>'
            f'<title>{_plain(step)}/{index}</title>'
            f'<text x="{x + _BOX_W / 2}" y="{y + _BOX_H / 2 + 4}" '
            f'text-anchor="middle">{_clip(step)}/{index}</text></g>')

    out.append("</svg>")
    return markupsafe.Markup("".join(out))


def _clip(step: str, width: int = 16) -> str:
    '''A name that fits the box. The full one is in the box's <title>, which
    is what a browser shows on hover -- so nothing is lost, only folded.'''
    if len(step) > width:
        step = step[:width - 1] + "\u2026"
    return _plain(step)


def _plain(value: str) -> str:
    return str(markupsafe.escape(value))


def _all_artifacts(session, job_id, args=None):
    '''Every artifact, following the cursor.

    ⚠️ The endpoint pages at 50 and caps at 200, which is right for an API and
    wrong for a screen: a forty-node flow produces more than either, and a page
    that silently shows the first fifty is a page that says *this run produced
    fifty things*. Bounded anyway, because a loop over somebody else's cursor
    should not be the thing that hangs a request.
    '''
    query = dict(args or {})
    query["limit"] = "200"

    items, seen = [], 0
    while seen < 20:
        page, cursor = _jobs().artifacts(session, job_id, query)
        items.extend(page)
        if not cursor:
            break
        query["cursor"] = cursor
        seen += 1

    return items


@blueprint.route("/portal/jobs/<job_id>/cancel", methods=["POST"])
@screen
def cancel(session, job_id):
    # Never None. `reason` is optional on the wire -- requiring it would make
    # a Ctrl-C inexpressible -- but a cancel with nothing recorded leaves a job
    # page that says only "cancelled", and the owner's own question is which of
    # their windows did it.
    reason = (flask.request.form.get("reason") or "").strip()
    _jobs().cancel(session, job_id, reason or "cancelled from the portal")
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/archive", methods=["POST"])
@screen
def archive(session, job_id):
    """Put a job away, or take it back out.

    ⚠️ The portal is the writer because the contract gives archiving no
    endpoint: it is a view preference, not an operation on the run. `archived_at`
    was published on every job object and nothing had ever set it.
    """
    _jobs().archive(session, job_id,
                    archived=flask.request.form.get("archived") == "1")
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/discard", methods=["POST"])
@screen
def discard(session, job_id):
    """Throw away what a run produced, and keep the run.

    🔴 Distinct from `delete` below, and the distinction is the one that was
    missing. This reclaims the bytes; the job stays in the list with its
    states, its timings and its artifact rows, so *where did my results go* is
    still answerable. Deleting the JOB takes it out of the collection.
    """
    job = _jobs().get(session, job_id)
    expected = f"{job['design']}/{job['jobname']}"

    if (flask.request.form.get("confirm") or "").strip() != expected:
        raise ProblemError(
            "invalid-request",
            detail=f"type {expected} to confirm discarding what this run produced")

    _jobs().discard_artifacts(session, job_id, "discarded from the portal")
    return flask.redirect(flask.url_for("portal.artifacts", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/delete", methods=["POST"])
@screen
def delete(session, job_id):
    '''Remove the job itself, which takes it out of every listing.

    ⚠️ The confirmation is a speed bump and not a security control -- CSRF is
    what stops somebody else pressing this. It is here because the button used
    to sit next to "Artifacts" on the job page, one position away from the link
    people click constantly, and the two do opposite things.

    🔴 This is the heavier of the two. `jobs.deleted_at` removes the job from
    the collection, so it is reachable only by id afterwards -- which is more
    than most people mean by "delete the results". That is what `discard`
    above is for.
    '''
    job = _jobs().get(session, job_id)
    expected = f"{job['design']}/{job['jobname']}"

    if (flask.request.form.get("confirm") or "").strip() != expected:
        raise ProblemError(
            "invalid-request",
            detail=f"type {expected} to confirm deleting what this run produced")

    _jobs().delete(session, job_id)
    return flask.redirect(flask.url_for("portal.jobs"))


######################################################################
# Artifacts and logs
######################################################################

@blueprint.route("/portal/jobs/<job_id>/artifacts", methods=["GET"])
@screen
def artifacts(session, job_id):
    detail = _jobs().get(session, job_id)
    items = _all_artifacts(session, job_id, flask.request.args)
    return flask.render_template("artifacts.html", job=detail, artifacts=items,
                                 kind=flask.request.args.get("kind", ""),
                                 step=flask.request.args.get("step", ""))


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


######################################################################
# Looking inside an archive
######################################################################

# What may be handed to a browser with a media type that lets it render.
#
# 🔴 A short allow-list rather than a guess from the extension, and the
# omissions are the point. An artifact is bytes a JOB produced, so a design
# that writes an HTML file would otherwise get it served from the portal's own
# origin -- stored cross-site scripting, with the run as the delivery
# mechanism. SVG is left out for the same reason: it is a document that can
# carry script, not a picture. Everything not on this list is served as plain
# text or downloaded, and nothing is ever served as text/html.
_RENDERABLE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Read into memory to show, and no further. A report is kilobytes; a DEF in the
# same archive is not, and a page is not where you read one.
MAX_INLINE_BYTES = 2 * 1024 * 1024

# 🔴 How large an archive this will open at all, and the reason is that a
# gzipped tar HAS NO INDEX. Listing what one holds means decompressing the
# whole stream, so a six-gigabyte bundle is a minute of a request thread before
# the first row is drawn -- and then again for the file somebody clicks. The
# object people actually want to read is the `reports` archive, which is
# kilobytes; above this the answer is to download the bundle, which costs the
# same bytes and does not hold a worker.
MAX_BROWSE_BYTES = 1024 * 1024 * 1024


def _stored_at(row):
    """Where the bytes of one artifact are, or a refusal."""
    if not fetchable(row):
        raise ProblemError("not-found", detail="those bytes are not available")

    storage = flask.current_app.config["SC_STORAGE"]
    return storage.artifact_path(row["storage_key"])


def _member(archive, wanted: str):
    """One entry, matched against the archive's own list.

    🔴 Matched rather than joined. The name comes from a query string, and a
    tar can hold `../` in a member name whatever this server does -- so nothing
    here builds a path out of what the caller sent. It is compared, and a name
    the archive does not contain simply is not found.
    """
    with tarfile.open(archive, "r:*") as tar:
        for entry in tar.getmembers():
            if entry.isfile() and entry.name == wanted:
                handle = tar.extractfile(entry)
                return entry, (handle.read(MAX_INLINE_BYTES + 1) if handle else b"")
    raise ProblemError("not-found", detail="that file is not in this archive")


@blueprint.route("/portal/jobs/<job_id>/artifacts/<artifact_id>/inside",
                 methods=["GET"])
@screen
def inside(session, job_id, artifact_id):
    """What one archive holds, and one file out of it.

    ⚠️ Served from the archive rather than from the build directory, and that
    is deliberate: the working tree is deleted when a job is, and the artifact
    is the thing with a retention date on it. Reading what is retained is the
    same answer the API would give.
    """
    detail = _jobs().get(session, job_id)
    row = _jobs().artifact(session, job_id, artifact_id)
    archive = _stored_at(row)

    # A log or a manifest is one file and has nothing to look inside. Showing
    # it is still what somebody clicked, so this is the viewer for both rather
    # than a refusal and a second screen.
    if row["media_type"] != "application/gzip":
        return _show_one(detail, row, archive)

    if (row["size_bytes"] or 0) > MAX_BROWSE_BYTES:
        raise ProblemError(
            "invalid-request",
            detail=f"this {row['kind']} is {units.size(row['size_bytes'])} and "
                   "a gzipped archive has no index, so opening it means "
                   "decompressing all of it. Download it instead")

    wanted = flask.request.args.get("file")
    if wanted:
        return _show(detail, row, archive, wanted)

    try:
        with tarfile.open(archive, "r:*") as tar:
            entries = sorted(
                ((entry.name, entry.size) for entry in tar.getmembers()
                 if entry.isfile()),
                key=lambda pair: pair[0])
    except (OSError, tarfile.TarError) as e:
        raise ProblemError(
            "not-found", detail=f"that archive could not be read: {e}") from None

    return flask.render_template("inside.html", job=detail, item=row,
                                 entries=entries)


def _show_one(detail, row, path):
    """An artifact that is a single file: the run's log, or a manifest."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_INLINE_BYTES + 1)
    except OSError as e:
        raise ProblemError(
            "not-found", detail=f"those bytes could not be read: {e}") from None

    try:
        text = data[:MAX_INLINE_BYTES].decode("utf-8")
    except UnicodeDecodeError:
        text = None

    return flask.render_template(
        "inside.html", job=detail, item=row, entries=None, name=row["kind"],
        nbytes=row["size_bytes"], image=False, text=text, whole=True,
        truncated=len(data) > MAX_INLINE_BYTES)


def _show(detail, row, archive, wanted: str):
    """One file, rendered where it safely can be."""
    entry, data = _member(archive, wanted)
    suffix = posixpath.splitext(wanted)[1].lower()

    if flask.request.args.get("raw"):
        media = _RENDERABLE.get(suffix)
        response = flask.make_response(data[:MAX_INLINE_BYTES])
        response.headers["Content-Type"] = media or "text/plain; charset=utf-8"
        # Belt and braces around the allow-list above: no sniffing, and a
        # policy that would stop anything that did slip through from running.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = \
            "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"
        response.headers["Cache-Control"] = "private, no-store"
        return response

    truncated = len(data) > MAX_INLINE_BYTES
    text = None
    if suffix not in _RENDERABLE:
        try:
            text = data[:MAX_INLINE_BYTES].decode("utf-8")
        except UnicodeDecodeError:
            text = None

    return flask.render_template(
        "inside.html", job=detail, item=row, entries=None, name=wanted,
        nbytes=entry.size, image=suffix in _RENDERABLE, text=text,
        truncated=truncated)


@blueprint.route("/portal/jobs/<job_id>/logs/<step>/<index>", methods=["GET"])
@screen
def log(session, job_id, step, index):
    '''One node's log: the archived bytes, or the live tail as it is written.'''
    detail = _jobs().get(session, job_id)

    # Every log this node left, so somebody looking for the TOOL's complaint is
    # not sent to SiliconCompiler's own record of the node.
    available = _jobs().node_logs(session, job_id, step, index)
    wanted = flask.request.args.get("file")
    chosen = next((name for name, _ in available if name == wanted),
                  available[0][0] if available else None)

    kind, target = _jobs().node_log(session, job_id, step, index)

    text, stream = "", None
    if kind == "artifact" or (chosen and available):
        picked = dict(available).get(chosen)
        if picked is not None:
            try:
                with open(picked, errors="replace") as handle:
                    text = handle.read()
            except OSError as e:
                text = f"(that log could not be read: {e})"
        else:
            # The working directory is gone; the archive is what is left.
            storage = flask.current_app.config["SC_STORAGE"]
            try:
                with open(storage.artifact_path(target["storage_key"]),
                          errors="replace") as handle:
                    text = handle.read()
            except OSError as e:
                text = f"(the archived log could not be read: {e})"

    if kind == "stream" and not text:
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

    return flask.render_template(
        "log.html", job=detail, step=step, index=index, text=text,
        stream=stream, available=[name for name, _ in available], chosen=chosen)


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
        limits=accounts.account_limits(
            config, accounts.effective_limits(_store(), config, session.user_id)),
        # Read-only, and the two numbers together are the whole story: what
        # this account gets, and what the deployment gives by default. A single
        # figure cannot say whether somebody set it.
        default_limits=config.limits,
        overridable=accounts.OVERRIDABLE,
        usage=accounts.usage(_store(), session.user_id),
        lifetime=accounts.lifetime(_store(), session.user_id),
        assurance=config["identity_assurance"],
        containers=config["containers"])


######################################################################
# What this deployment is
######################################################################

@blueprint.route("/portal/server", methods=["GET"])
@screen
def deployment(session):
    """`GET /v1` and `GET /v1/healthz`, as a page.

    🔴 Built by CALLING the endpoints' own code, not by reading config and
    hoping it matches. `capabilities` and `healthz` are the two answers a
    client branches on, and a screen that renders a second opinion of them is
    a screen that can disagree with the API about what this server promises --
    which is worse than no screen, because somebody would trust it.

    ⚠️ The raw JSON is on the page too, folded away. This deployment is a
    reference implementation, so *what does `GET /v1` actually return* is a
    question its own portal should be able to answer without curl.
    """
    from siliconcompiler.remote.server.routes import meta

    config = flask.current_app.config["SC_CONFIG"]
    store = _store()

    published = config.capabilities(meta.advertised_software(store, config))

    # The same read the liveness probe makes, and the same three answers. It is
    # cheap on purpose -- a probe is scraped every few seconds.
    with flask.current_app.test_request_context("/v1/healthz"):
        health = json.loads(meta.healthz().get_data())

    return flask.render_template(
        "server.html", published=published, health=health,
        pretty=json.dumps(published, indent=2, sort_keys=True),
        containers=config["containers"],
        cluster=flask.current_app.config.get("SC_CLUSTER"))


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


@blueprint.route("/portal/images/software/<name>/retire", methods=["POST"])
@screen
def retire_software(session, name):
    '''Withdraw the claim that this deployment curates a distribution.

    🔴 Not the same as retiring its last version, and the difference is
    load-bearing: retiring a VERSION says *not this one*, and a flow needing
    that tool is still refused unless an image holds another. Retiring the
    SOFTWARE says *not any more*, and the tool stops raising a requirement at
    all -- which hands its nodes back to the job's own image.
    '''
    version = flask.request.form.get("version")
    if version:
        images.retire_version(_store(), name, version, session.user_id)
    else:
        images.retire_software(_store(), name, session.user_id)

    return flask.redirect(flask.url_for("portal.registry"))


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
