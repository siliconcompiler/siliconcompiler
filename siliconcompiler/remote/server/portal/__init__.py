'''
The portal: ten screens over the same decisions the API makes.

🔴 Every authorization decision goes through the code the API handlers call
(``JobService.owned``, ``accounts.owned_device``...): a portal query that
forgets ``WHERE user_id =`` answers ``200`` and looks correct.

⚠️ It does not call its own API over HTTP: a browser holds no device key, so it
reads the shared layer, and every bytes link is a signed storage URL. 🔴 A
portal session is a cookie and never becomes an API credential: that would be
the shortest way around the key pinning.
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

from siliconcompiler.utils.units import format_binary, format_duration
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.identity import accounts
from siliconcompiler.remote.server.identity.auth import SCOPES, Session
from siliconcompiler.remote.server.jobs import MAX_REASON
from siliconcompiler.remote.server.outputs.artifacts import UNOPENED, fetchable, unopened
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.storage import DOWNLOAD_SECONDS

__all__ = ["blueprint", "Sessions"]


logger = logging.getLogger("sc-server")

blueprint = flask.Blueprint("portal", __name__, template_folder="templates")


COOKIE = "sc_portal"

# Short and single-use: the URL lands in browser history and maybe an access log.
HANDOVER_SECONDS = 60

# The page somebody was turned away from: a breadcrumb, not a credential, and
# untrusted input.
NEXT_COOKIE = "sc_portal_next"
HANDOVER_NEXT_SECONDS = 900

# Not the API's twelve days: another session costs one command.
SESSION_SECONDS = 43200


class Sessions:
    '''Browser sessions, in memory and nowhere else.

    🔴 Deliberately not a table: losing one on restart costs ``sc-remote -portal``.
    '''

    def __init__(self):
        self._handovers = {}
        self._sessions = {}
        self._lock = threading.Lock()

    def offer(self, user_id: str, landing=None):
        """Mint a single-use token for one browser; returns ``(token, epoch expiry)``.

        `landing` is built by the caller from an id: this class stores what it is given.
        """
        token = secrets.token_urlsafe(32)
        expires = time.time() + HANDOVER_SECONDS
        with self._lock:
            self._expire()
            self._handovers[token] = (user_id, expires, landing)
        return token, expires

    def redeem(self, token: str):
        '''Spend a handover token; returns ``(cookie, csrf, landing)`` or None.

        🔴 Removed before it is checked, so two requests together cannot both redeem it.
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
        '''``(user_id, csrf, when it ends)`` for a live session, or None.'''
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
            return user_id, csrf, expires

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


def _sessions() -> Sessions:
    return flask.current_app.config["SC_PORTAL"]


def _jobs():
    return flask.current_app.config["SC_JOBS"]


def _store():
    return flask.current_app.config["SC_STORE"]


def _held():
    '''This request's live session (`Sessions.lookup`), looked up once per request.'''
    if "sc_portal_session" not in flask.g:
        flask.g.sc_portal_session = _sessions().lookup(flask.request.cookies.get(COOKIE))
    return flask.g.sc_portal_session


def caller():
    '''The signed-in user, as the same Session object the API builds.

    🔴 So there is no second notion of who is asking. ⚠️ The full scope set is
    what the API offers this person; it is not a credential for ``/v1``.
    '''
    held = _held()
    if held is None:
        return None

    user_id, _csrf, expires = held
    return Session(user_id=user_id, scope=" ".join(SCOPES),
                   family_id=None, device_id=None, jkt=None, expires_at=expires)


def screen(handler):
    '''A page that needs a session, rendering refusals as pages.'''
    from functools import wraps

    @wraps(handler)
    def guarded(*args, **kwargs):
        session = caller()
        if session is None:
            # 🔴 Remember where they were going, in a cookie: the CLI that mints
            # the handover never sees this request.
            page = flask.make_response(flask.render_template("signin.html"), 401)
            if flask.request.method == "GET":
                page.set_cookie(
                    NEXT_COOKIE, flask.request.path,
                    max_age=HANDOVER_NEXT_SECONDS, httponly=True,
                    samesite="Strict", secure=flask.request.is_secure)
            return page

        if flask.request.method == "POST" and not secrets.compare_digest(
                flask.request.form.get("csrf", ""), _held()[1]):
            # Beside SameSite=Strict, for a browser too old to honour it.
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


@blueprint.app_template_filter("runtime")
def _runtime(node) -> str:
    '''How long a node took, or how long it has been going.'''
    started, finished = node.get("started_at"), node.get("finished_at")
    if not started:
        return "\u2014"

    end = _epoch(finished) if finished else time.time()
    begin = _epoch(started)
    if end is None or begin is None:
        return "\u2014"

    return format_duration(max(0, int(end - begin)))


@blueprint.app_context_processor
def _limits():
    """What the templates need to not offer a link this will refuse."""
    return {"browse_limit": MAX_BROWSE_BYTES}


@blueprint.app_template_filter("size")
def _size(num_bytes) -> str:
    """Bytes as a person reads them, in binary units, as the CLI shows them."""
    return format_binary(num_bytes, "B", digits=1, show_unit=True, compact=True,
                         default="—")


@blueprint.app_template_filter("digest")
def _digest(digest) -> markupsafe.Markup:
    """A digest, short enough for a table and whole on hover."""
    if not digest:
        return markupsafe.Markup('<span class="muted">\u2014</span>')
    text = str(digest)
    algorithm, _, hexdigest = text.partition(":")
    short = f"{algorithm}:{hexdigest[:12]}\u2026" if hexdigest else text
    return markupsafe.Markup(
        f'<code class="mono" title="{markupsafe.escape(text)}">'
        f'{markupsafe.escape(short)}</code>')


@blueprint.app_template_filter("duration")
def _duration(seconds) -> str:
    return format_duration(seconds)


@blueprint.app_template_filter("when")
def _when(timestamp) -> markupsafe.Markup:
    '''One instant, as the reader's own clock shows it.

    🔴 The server cannot know the browser's timezone, and a zoneless time looks
    right while being wrong. So it goes out as UTC in a `<time datetime>`, and
    a small inline script rewrites it to local. ⚠️ The page stays correct
    with scripting off, and there is still no JavaScript build.
    '''
    if not timestamp:
        return markupsafe.Markup('<span class="muted">\u2014</span>')

    text = str(timestamp)
    # What a reader sees if the script never runs.
    readable = text[:19].replace("T", " ") + " UTC"
    return markupsafe.Markup(
        f'<time datetime="{markupsafe.escape(text)}" '
        f'class="ts">{markupsafe.escape(readable)}</time>')


def _epoch(stamp: Optional[str]) -> Optional[float]:
    from siliconcompiler.remote.server.state.store import parse

    if not stamp:
        return None
    try:
        return parse(stamp).timestamp()
    except ValueError:
        return None


@blueprint.app_context_processor
def _csrf_for_templates():
    held = _held() if flask.has_request_context() else None
    return {"csrf": held[1] if held else ""}


@blueprint.route("/portal/enter")
def enter():
    '''Exchange the token for a cookie, and destroy the token.'''
    redeemed = _sessions().redeem(flask.request.args.get("token", ""))
    if redeemed is None:
        return flask.render_template(
            "problem.html", title="That link has been used or has expired",
            detail="Run sc-remote -portal again to get a new one."), 403

    cookie, _csrf, landing = redeemed

    # 🔴 The handover's own destination first, then the breadcrumb.
    # 🔴 The breadcrumb only as a local `/portal/` path, never `//`: anything
    # can set a cookie here, and following one blindly is an open redirect.
    wanted = flask.request.cookies.get(NEXT_COOKIE)
    if not (isinstance(wanted, str) and wanted.startswith("/portal/")):
        wanted = None
    response = flask.redirect(landing or wanted or flask.url_for("portal.jobs"))
    response.delete_cookie(NEXT_COOKIE, samesite="Strict")
    response.set_cookie(
        COOKIE, cookie, max_age=SESSION_SECONDS, httponly=True,
        samesite="Strict",
        # On a permitted plaintext deployment a Secure cookie would never arrive.
        secure=flask.request.is_secure)
    return response


@blueprint.route("/portal/logout", methods=["POST"])
def logout():
    _sessions().end(flask.request.cookies.get(COOKIE))
    response = flask.redirect(flask.url_for("portal.jobs"))
    response.delete_cookie(COOKIE)
    return response


@blueprint.route("/portal/", methods=["GET"])
@screen
def jobs(session):
    args = dict(flask.request.args)
    args.setdefault("limit", "50")
    items, _cursor = _jobs().listing(session, args)

    # 🔴 `archived` deliberately has no value meaning both: a mixed list is what
    # archiving exists to end.
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

    # 🔴 Every page followed: the raw (items, cursor) tuple renders silently empty.
    items = _all_artifacts(session, job_id)

    per_node = {}
    for item in items:
        per_node.setdefault((item["step"], item["index"]), []).append(item)

    # 🔴 The run's order, as the picture beside it, not the API's alphabetical one.
    detail["nodes"] = running_order(detail, edges)

    return flask.render_template(
        "job.html", job=detail, edges=edges, history=history,
        placements=_jobs().node_placements(session, job_id), per_node=per_node,
        job_level=per_node.get((None, None), []),
        job_log=next((item for item in per_node.get((None, None), [])
                      if item["kind"] == "logs" and item["fetchable"]), None),
        # Beside the run's log, never inside it (surface D295).
        staging_log=next((item for item in per_node.get((None, None), [])
                          if item["kind"] == "staging" and item["fetchable"]), None),
        diagnostics=next((item for item in per_node.get((None, None), [])
                          if item["kind"] == "diagnostics" and item["fetchable"]), None),
        graph=_graph(detail, edges))


# ⚠️ Laid out downwards: a flow is deep and narrow, so across would be a scrollbar.
_BOX_W, _BOX_H, _GAP_X, _GAP_Y, _PAD = 132, 28, 14, 22, 12


def _depths(nodes, edges):
    """Each node's level in `Flowgraph.get_execution_order`.

    🔴 One number lays out the picture and sorts the table, so the two agree.
    Built from the job's rows as no-op nodes: the portal never reads the manifest.
    """
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    known = set(nodes)
    try:
        flow = Flowgraph("portal")
        for step, index in nodes:
            flow.node(step, NOPTask(), index=index)
        for edge in edges:
            source = (edge["from_step"], edge["from_index"])
            target = (edge["to_step"], edge["to_index"])
            if source in known and target in known:
                flow.edge(source[0], target[0], tail_index=source[1], head_index=target[1])
        # A cycle cannot happen, and a layout routine must not loop on one.
        if flow.validate(logger=logging.getLogger("sc-server")):
            return {node: level for level, row in enumerate(flow.get_execution_order())
                    for node in row}
    except ValueError:
        pass
    return {node: 0 for node in nodes}


def running_order(job, edges):
    """The job's nodes in the order the run reaches them, ties broken by name.

    ⚠️ The API's by-name order puts `elaborate` between `cts` and `floorplan`.
    """
    nodes = [(node["step"], node["index"]) for node in job.get("nodes") or []]
    depth = _depths(nodes, edges)

    return sorted(job.get("nodes") or [],
                  key=lambda node: (depth.get((node["step"], node["index"]), 0),
                                    node["step"], node["index"]))


def _graph(job, edges):
    '''The flowgraph as inline SVG, drawn here: 🔴 the portal has no JavaScript build.

    A node's row is its depth (:func:`_depths`); within a row, listing order.
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
        # The full name is in the <title>, shown on hover.
        clipped = step if len(step) <= 16 else step[:15] + "\u2026"
        out.append(
            f'<g class="node {states.get(node, "pending")}">'
            f'<rect x="{x}" y="{y}" width="{_BOX_W}" height="{_BOX_H}" rx="5"/>'
            f'<title>{_plain(step)}/{index}</title>'
            f'<text x="{x + _BOX_W / 2}" y="{y + _BOX_H / 2 + 4}" '
            f'text-anchor="middle">{_plain(clipped)}/{index}</text></g>')

    out.append("</svg>")
    return markupsafe.Markup("".join(out))


def _plain(value: str) -> str:
    return str(markupsafe.escape(value))


def _all_artifacts(session, job_id, args=None):
    '''Every artifact, following the cursor, boundedly.

    ⚠️ A screen showing only the first page would misstate what the run produced.
    '''
    query = dict(args or {})
    query["limit"] = "200"

    items, seen = [], 0
    while seen < 20:
        page, cursor = _jobs().artifacts(session, job_id, query, surface="portal")
        items.extend(page)
        if not cursor:
            break
        query["cursor"] = cursor
        seen += 1

    return items


@blueprint.route("/portal/jobs/<job_id>/cancel", methods=["POST"])
@screen
def cancel(session, job_id):
    # Never empty: the owner's question is which of their windows cancelled it.
    reason = (flask.request.form.get("reason") or "").strip()
    _jobs().cancel(session, job_id, reason or "cancelled from the portal")
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/archive", methods=["POST"])
@screen
def archive(session, job_id):
    """Put a job away, or take it back out: ⚠️ a view preference with no API endpoint."""
    _jobs().archive(session, job_id,
                    archived=flask.request.form.get("archived") == "1")
    return flask.redirect(flask.url_for("portal.job", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/discard", methods=["POST"])
@screen
def discard(session, job_id):
    """Throw away what a run produced, and keep the run and its artifact rows.

    🔴 Distinct from `delete`, which takes the job out of the collection.
    """
    job = _jobs().get(session, job_id)
    expected = f"{job['design']}/{job['jobname']}"

    if (flask.request.form.get("confirm") or "").strip() != expected:
        raise ProblemError(
            "invalid-request",
            detail=f"type {expected} to confirm discarding what this run produced")

    # A supplied reason carries the attribution, never a published user id.
    reason = " ".join((flask.request.form.get("reason") or "").split())
    _jobs().discard_artifacts(
        session, job_id,
        reason[:MAX_REASON] or f"discarded by {_jobs().whodunnit(session)}")
    return flask.redirect(flask.url_for("portal.artifacts", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/discard-node", methods=["POST"])
@screen
def discard_node(session, job_id):
    """Throw away one node's output.

    🔴 The node, not one artifact: its rows share bytes, so one row alone frees
    nothing. ⚠️ No typed confirmation per row, or confirmations stop being read.
    """
    step = (flask.request.form.get("step") or "").strip()
    index = (flask.request.form.get("index") or "").strip()
    if not step or not index:
        raise ProblemError("invalid-request", detail="step and index are required")

    _jobs().discard_node(session, job_id, step, index,
                         f"discarded by {_jobs().whodunnit(session)}")
    return flask.redirect(flask.url_for("portal.artifacts", job_id=job_id))


@blueprint.route("/portal/jobs/<job_id>/delete", methods=["POST"])
@screen
def delete(session, job_id):
    '''Remove the job itself, reachable only by id afterwards.

    ⚠️ The confirmation is a speed bump, not a security control (CSRF is).
    🔴 The heavier of the two; `discard` is what most people mean.
    '''
    job = _jobs().get(session, job_id)
    expected = f"{job['design']}/{job['jobname']}"

    if (flask.request.form.get("confirm") or "").strip() != expected:
        raise ProblemError(
            "invalid-request",
            detail=f"type {expected} to confirm deleting what this run produced")

    _jobs().delete(session, job_id)
    return flask.redirect(flask.url_for("portal.jobs"))


@blueprint.route("/portal/jobs/<job_id>/artifacts", methods=["GET"])
@screen
def artifacts(session, job_id):
    detail = _jobs().get(session, job_id)
    items = _all_artifacts(session, job_id, flask.request.args)
    uploads = _uploads(items, detail)
    shown = {item["id"] for item in uploads}
    return flask.render_template("artifacts.html", job=detail, artifacts=items,
                                 uploads=uploads,
                                 groups=_by_node([item for item in items
                                                  if item["id"] not in shown]),
                                 reason_chars=MAX_REASON,
                                 kind=flask.request.args.get("kind", ""),
                                 step=flask.request.args.get("step", ""))


def _uploads(items, job):
    """Every upload the job took, in order; the last marked `unopened` per `UNOPENED`."""
    uploads = sorted((dict(item) for item in items
                      if item.get("kind") == "input" and item.get("step") is None),
                     key=lambda item: (item.get("created_at") or "", item.get("id") or ""))
    refusal = ((job.get("error") or {}).get("type") or "").rsplit("/", 1)[-1]
    if uploads and refusal in UNOPENED:
        uploads[-1]["unopened"] = refusal
    return uploads


def _by_node(items):
    """The listing grouped by node, job-level objects first.

    🔴 The node is the unit of deletion (`discard_node`), so its button sits
    against all its rows.
    """
    groups, seen = [], {}

    for item in items:
        key = (item.get("step"), item.get("index"))
        if key not in seen:
            seen[key] = {"step": key[0], "index": key[1], "items": []}
            groups.append(seen[key])
        seen[key]["items"].append(item)

    return sorted(groups, key=lambda group: (group["step"] is not None,))


@blueprint.route("/portal/jobs/<job_id>/artifacts/<artifact_id>", methods=["GET"])
@screen
def fetch(session, job_id, artifact_id):
    '''Hand the browser a signed URL for the bytes, after the API's own refusals.

    🔴 The signature is the credential; a cookie never authorises a download.
    ⚠️ The one difference, explicit as `surface="portal"`: `max_download_bytes`
    and `api_fetchable_kinds` are lifted for a person clicking one object.
    '''
    row = _jobs().artifact(session, job_id, artifact_id, surface="portal")
    storage = flask.current_app.config["SC_STORAGE"]

    expires = int(time.time()) + DOWNLOAD_SECONDS
    signature = storage.sign_download(row["id"], expires)

    return flask.redirect(flask.url_for(
        "artifacts.download", job_id=job_id, artifact_id=row["id"],
        expires=expires, sig=signature))


# 🔴 What a browser may render: a short allow-list, the omissions the point. A
# job's HTML or SVG served from this origin would be stored XSS; everything else
# is plain text or a download, never text/html.
_RENDERABLE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Read into memory to show, and no further.
MAX_INLINE_BYTES = 2 * 1024 * 1024

# 🔴 The largest archive opened at all: a gzipped tar has no index, so listing
# one decompresses it whole on a request thread. Above this, download it.
MAX_BROWSE_BYTES = 1024 * 1024 * 1024


def _stored_at(row):
    """Where one artifact's bytes are, admin view (ladder row 3), or a refusal."""
    if not fetchable(row, admin=True):
        raise ProblemError("not-found", detail="those bytes are not available")

    storage = flask.current_app.config["SC_STORAGE"]
    return storage.artifact_path(row["storage_key"])


def _member(archive, wanted: str):
    """One entry, matched against the archive's own list.

    🔴 Matched, never joined into a path: the name comes from a query string.
    🔴 A regular member only (surface D159): `extractfile` follows links, and
    `isfile()` is false for both kinds.
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

    ⚠️ From the archive, deliberately not the build directory: the artifact is
    what is retained.
    """
    detail = _jobs().get(session, job_id)
    # As the download, and only one bounded member leaves the server.
    row = _jobs().artifact(session, job_id, artifact_id, surface="portal")

    # 🔴 Never opened (`UNOPENED`): the refusal is shown instead.
    job = _jobs().owned(session, job_id)
    if unopened(_store(), row, job["error_type"]):
        return flask.render_template("inside.html", job=detail, item=row,
                                     entries=None, refused=detail.get("error") or {})

    archive = _stored_at(row)

    # A single-file artifact is shown here too.
    one_file = row["kind"] in ("manifest", "staging") or (
        row["kind"] == "logs" and row["step"] is None)
    if one_file:
        return _show_one(detail, row, archive)

    if (row["size_bytes"] or 0) > MAX_BROWSE_BYTES:
        raise ProblemError(
            "invalid-request",
            detail=f"this {row['kind']} is {_size(row['size_bytes'])} and "
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
    """An artifact that is a single file: the run's log, the staging record, or a manifest."""
    import gzip

    try:
        with gzip.open(path, "rb") as handle:
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
        # Belt and braces around the allow-list: no sniffing, and no script runs.
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


@blueprint.route("/portal/jobs/<job_id>/metrics/<step>/<index>", methods=["GET"])
@screen
def metrics(session, job_id, step, index):
    '''One node's metrics and records, 🔴 from the table, never a manifest parse (contract §1).'''
    detail = _jobs().get(session, job_id)
    found = _jobs().node_metrics(session, job_id, step, index)
    if found is None:
        flask.abort(404)
    return flask.render_template(
        "metrics.html", job=detail, step=step, index=index,
        metrics=sorted((found["metrics"] or {}).items()),
        records=sorted((found["records"] or {}).items()))


@blueprint.route("/portal/jobs/<job_id>/logs/<step>/<index>", methods=["GET"])
@screen
def log(session, job_id, step, index):
    '''One node's log: the archived bytes, or the live tail as it is written.'''
    from siliconcompiler.remote.server.state.store import TERMINAL_NODE_STATES

    detail = _jobs().get(session, job_id)

    # Every log this node left, the tool's as well as SiliconCompiler's.
    available = _jobs().node_logs(session, job_id, step, index)
    wanted = flask.request.args.get("file")
    chosen = next((name for name, _ in available if name == wanted),
                  available[0][0] if available else None)

    node = _jobs().node_log(session, job_id, step, index, surface="portal")
    finished = node["state"] in TERMINAL_NODE_STATES

    text, stream = "", None
    picked = dict(available).get(chosen)
    if picked is not None:
        try:
            text = _jobs().read_node_file(session, job_id, picked)
        except OSError:
            # Never explained: the reason is about this server's tree.
            text = "(that log could not be read)"
    elif finished:
        # The working directory is gone; the archive is what is left.
        from siliconcompiler.remote.server.outputs import artifacts

        row = flask.current_app.config["SC_STORE"].one(
            "SELECT * FROM artifacts WHERE job_id = ? AND step = ? AND \"index\" = ? "
            "AND kind = 'logs' AND deleted_at IS NULL", (job_id, step, index))
        try:
            text = artifacts.log_text(flask.current_app.config["SC_STORAGE"], row)
        except (OSError, TypeError, ValueError) as e:
            text = f"(the archived log could not be read: {e})"

    if not finished and not text:
        # The CLI's signed stream URL, bounded by the portal session.
        storage = flask.current_app.config["SC_STORAGE"]
        expires = int(session.expires_at or time.time())
        nonce = secrets.token_urlsafe(8)
        stream = flask.url_for(
            "artifacts.tail", job_id=job_id, step=step, index=index,
            expires=expires, n=nonce,
            sig=storage.sign_stream(job_id, step, index, expires, nonce))

    return flask.render_template(
        "log.html", job=detail, step=step, index=index, text=text,
        stream=stream, available=[name for name, _ in available], chosen=chosen)


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
        default_limits=config.limits,
        overridable=accounts.OVERRIDABLE,
        usage=accounts.usage(_store(), session.user_id),
        lifetime=accounts.lifetime(_store(), session.user_id),
        assurance=config["identity_assurance"],
        containers=config["containers"])


@blueprint.route("/portal/server", methods=["GET"])
@screen
def deployment(session):
    """`GET /v1` and `GET /v1/healthz`, as a page, with the raw JSON folded away.

    🔴 Built by calling the endpoints' own code, so it can never disagree with
    the API about what this server promises.
    """
    from siliconcompiler.remote.server.routes import meta

    config = flask.current_app.config["SC_CONFIG"]
    store = _store()

    published = config.capabilities(meta.advertised_software(store, config))

    health = {"status": meta.health_status(store)}

    return flask.render_template(
        "server.html", published=published, health=health,
        pretty=json.dumps(published, indent=2, sort_keys=True),
        containers=config["containers"],
        cluster=flask.current_app.config.get("SC_CLUSTER"))


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

    # 🔴 Stated, not derived (`images.register_software`).
    kind = flask.request.form.get("kind")
    driver = (flask.request.form.get("driver") or "").strip() or None
    if kind not in ("python", "tool"):
        raise ProblemError(
            "invalid-request",
            detail="say whether this is a python distribution or a tool")

    try:
        images.register_software(
            _store(), name, flask.request.form.get("display") or name,
            session.user_id, kind, driver=driver,
            version_package=(flask.request.form.get("version_package")
                             or "").strip() or None,
            allowed_drivers=flask.current_app.config["SC_CONFIG"]["software_drivers"])
    except ValueError as e:
        raise ProblemError("invalid-request", detail=str(e)) from None

    try:
        preference = int(flask.request.form.get("preference"))
    except (TypeError, ValueError):
        preference = 0
    if version:
        images.register_version(
            _store(), name, version, session.user_id,
            preference=preference,
            source=("published_date" if flask.request.form.get("unversioned")
                    else "reported"))

    return flask.redirect(flask.url_for("portal.registry"))


@blueprint.route("/portal/images/register", methods=["POST"])
@screen
def register_image(session):
    '''🔴 The most dangerous write (`images.register_image`): it records the person.'''
    ref = (flask.request.form.get("ref") or "").strip()
    digest = (flask.request.form.get("digest") or "").strip()
    contains = [line.strip() for line
                in (flask.request.form.get("contains") or "").splitlines()
                if line.strip()]

    try:
        image_id = images.register_image(
            _store(), ref, digest, images._contains(contains), session.user_id,
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
                "not-ready", status=503,
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

    🔴 Not the same as retiring its last version (`images.live_software`).
    '''
    version = flask.request.form.get("version")
    if version:
        images.retire_version(_store(), name, version, session.user_id)
    else:
        images.retire_software(_store(), name, session.user_id)

    return flask.redirect(flask.url_for("portal.registry"))
