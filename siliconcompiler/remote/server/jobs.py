'''
The job: creating one, feeding it bytes, running it, and saying what it did.

Everything above this module is HTTP and everything below it is a filesystem or
a scheduler. The ordering rules that matter are here, and one of them is a
security property rather than a preference:

🔴 **submit checks the digest against what storage reports, refuses before any
extraction, and only then re-derives the manifest and re-runs every check
against what was re-derived.** Getting that order wrong is how an archive bomb
gets opened. Nothing in this file may be reordered without reading that sentence
again.
'''

import base64
import json
import logging
import re
import shutil
import sqlite3

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.remote.server import archive, artifacts, images, runspec
from siliconcompiler.remote.server.dispatch import DispatchError
from siliconcompiler.remote.server.errors import ERRORS, ProblemError, TYPE_BASE
from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now
from siliconcompiler.remote.server.storage import GRANT_SECONDS

__all__ = ["JobService", "TERMINAL_STATES", "REUSABLE_STATES"]


logger = logging.getLogger("sc-server")


# Published on the job object, so a client reads `terminal` and never switches
# on the name. The set has grown twice already.
TERMINAL_STATES = frozenset(
    ("completed", "failed", "cancelled", "rejected", "abandoned"))
TERMINAL_NODE_STATES = frozenset(("completed", "failed", "skipped", "cancelled"))

# Job reuse returns a result the hash determines and never a refusal it does
# not: `rejected` is an entitlement decision about a person at a moment, and
# `cancelled` and `abandoned` are somebody having stopped.
REUSABLE_STATES = ("completed", "failed")

# Long enough for any real design or job name and short enough that the column,
# the path and the log line all stay sane.
MAX_NAME = 100
MAX_REASON = 500

# `design` and `jobname` become path segments under the job's own root, so they
# are checked rather than trusted. The manifest's own copies are checked again
# at submit against the same rule -- an upload is the other end of this.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class JobService:
    '''One deployment's jobs.

    Built once and held on the app, because it owns the dispatcher -- which for
    a local deployment holds the handles to the processes it started.
    '''

    def __init__(self, store, config, storage, dispatcher, datadir):
        self._store = store
        self._config = config
        self._storage = storage
        self._dispatcher = dispatcher
        self._datadir = Path(datadir)

    ######################################################################
    # Where a user's work lives
    ######################################################################

    def user_root(self, user_id: str) -> Path:
        return self._datadir / "users" / user_id

    def builds_root(self, user_id: str) -> Path:
        return self.user_root(user_id) / "builds"

    def cache_dir(self, user_id: str) -> Path:
        return self.user_root(user_id) / "cache"

    def job_root(self, user_id: str, job_id: str) -> Path:
        '''The build directory for one job of one user.

        Per user as well as per job. The ownership record is `jobs.user_id`, in
        the store, rather than a file inside the directory it protects -- which
        is what the tree it replaces did.
        '''
        return self.builds_root(user_id) / job_id

    ######################################################################
    # 13. create
    ######################################################################

    def create(self, session, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Tuple[Dict[str, Any], int]:
        '''Returns the job object and the status it should be served with.'''
        if not isinstance(body, dict):
            raise ProblemError("invalid-request", detail="the body must be a JSON object")

        if body.get("project") is not None:
            # Refused rather than ignored: silently dropping it creates a job
            # the caller believes is shared and nobody else can see, which is a
            # failure invisible from both ends. Permanent, so a client stops
            # offering the picker.
            raise ProblemError(
                "feature-unsupported", feature="projects",
                detail="this deployment has no projects; every job is personal")

        design = _name(body.get("design"), "design")
        jobname = _name(body.get("jobname"), "jobname")
        run_hash = _opaque(body.get("run_hash"), "run_hash")

        if idempotency_key is not None:
            existing = self._store.one(
                "SELECT * FROM jobs WHERE user_id = ? AND idempotency_key = ?",
                (session.user_id, idempotency_key))
            if existing is not None:
                # The same key with a different body is the caller having reused
                # a key they should have rotated. Returning the first job would
                # answer a question they did not ask.
                if json.loads(existing["descriptor"]) != body:
                    raise ProblemError(
                        "idempotency-key-reuse",
                        detail="this Idempotency-Key was used for a different request")
                return self.wire(existing), 200

        if run_hash:
            hit = self._reuse(session.user_id, run_hash)
            if hit is not None:
                # 200 rather than 201: a 201 carrying an old job's id is
                # indistinguishable from a new one. The body is the job object
                # either way, so a client that ignores the status is still
                # correct.
                logger.info(f"run_hash hit for {session.user_id}: {hit['id']}")
                return self.wire(hit), 200

        self._check_pending_uploads(session.user_id)
        self._check_descriptor(body)

        job_id = str(uuid7())
        device_id = session.device_id

        with self._store.transaction():
            self._store.execute(
                "INSERT INTO jobs (id, user_id, device_id, state, design, jobname, "
                "                  descriptor, idempotency_key, run_hash, retention_until) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?)",
                (job_id, session.user_id, device_id, design, jobname,
                 json.dumps(body), idempotency_key, run_hash,
                 _retention(self._config.limits["job_retention_days"])))
            self._transition(job_id, None, "created", actor=session.user_id)

        return self.wire(self._row(job_id)), 201

    def _reuse(self, user_id: str, run_hash: str):
        '''The caller's own newest job with this hash, if it may be handed back.

        🔴 Owner-scoped, and that is the whole safety argument. The hash is the
        client's and the server never recomputes or normalises it, so a wrong
        one hands a user their own stale job -- confusing, and not a disclosure.
        An archived job is excluded, which is how a person says *stop handing me
        that result* without an endpoint for it.
        '''
        placeholders = ", ".join("?" * len(REUSABLE_STATES))
        return self._store.one(
            "SELECT * FROM jobs WHERE user_id = ? AND run_hash = ? "
            f"  AND state IN ({placeholders}) "
            "  AND deleted_at IS NULL AND archived_at IS NULL "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (user_id, run_hash, *REUSABLE_STATES))

    def _check_pending_uploads(self, user_id: str) -> None:
        held = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            "AND state IN ('created', 'awaiting_input')", (user_id,))["n"]
        ceiling = self._config.limits["pending_uploads"]
        if held >= ceiling:
            raise ProblemError(
                "limit-exceeded", limit="pending_uploads",
                detail=f"{held} jobs are already waiting for their upload",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    def _check_descriptor(self, body: Dict[str, Any]) -> None:
        '''The early reject, on whatever is present.

        Client-asserted, so this is a hint and not a boundary -- every value is
        re-derived at submit. It exists to save an upload, and it never refuses
        a descriptor for being sparse: a missing field skips the check it would
        have answered.
        '''
        limits = self._config.limits

        flow = body.get("flow") or {}
        if isinstance(flow, dict) and isinstance(flow.get("nodes"), int):
            if flow["nodes"] > limits["max_job_nodes"]:
                raise ProblemError(
                    "node-limit-exceeded", limit="max_job_nodes",
                    detail=f"{flow['nodes']} nodes, and this server runs at most "
                           f"{limits['max_job_nodes']}")

        resources = body.get("resources") or {}
        if isinstance(resources, dict) and isinstance(resources.get("upload_bytes"), int):
            if resources["upload_bytes"] > limits["max_upload_bytes"]:
                raise ProblemError(
                    "upload-too-large", limit="max_upload_bytes",
                    detail=f"{resources['upload_bytes']} bytes, and this server "
                           f"accepts at most {limits['max_upload_bytes']}")

        versions = body.get("versions") or {}
        if isinstance(versions, dict) and versions:
            self._check_versions(versions)

    def _check_versions(self, versions: Dict[str, Any]) -> None:
        '''Refuse a client this deployment cannot run.

        The same comparison the client could have made itself against `GET /v1`'s
        `software`, which is the point of publishing it -- but a client that
        omitted `versions` reaches this check at submit instead, after the whole
        archive has moved.
        '''
        from siliconcompiler.remote.server.routes.meta import advertised_software

        available = advertised_software(self._store, self._config)
        for name, wanted in versions.items():
            if name not in available:
                continue
            if wanted not in available[name]:
                raise ProblemError(
                    "version-skew",
                    detail=f"this server runs {name} "
                           f"{', '.join(available[name])}, and you have {wanted}")

    ######################################################################
    # 14. upload-grant
    ######################################################################

    def grant(self, session, job_id: str, url_root: str) -> Dict[str, Any]:
        job = self.owned(session, job_id)

        if job["state"] not in ("created", "awaiting_input"):
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} takes no upload")

        descriptor = json.loads(job["descriptor"])
        declared = (descriptor.get("resources") or {}).get("upload_bytes")
        ceiling = self._config.limits["max_upload_bytes"]
        if isinstance(declared, int) and 0 < declared <= ceiling:
            ceiling = declared

        expires = int(_epoch()) + GRANT_SECONDS
        signature = self._storage.sign_upload(job["id"], ceiling, expires)

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_key = ?, upload_location_id = ?, "
                "  upload_grant_expires_at = ?, upload_revoked_at = NULL WHERE id = ?",
                (job["id"], self._config["storage_location_id"],
                 _from_epoch(expires), job["id"]))
            if job["state"] == "created":
                self._transition(job["id"], "created", "awaiting_input",
                                 actor=session.user_id)

        url = (f"{url_root.rstrip('/')}/storage/upload/{job['id']}"
               f"?max_bytes={ceiling}&expires={expires}&sig={signature}")

        return {
            "method": "PUT",
            "url": url,
            # A ceiling rather than an exact length, and the signature carries
            # the same number: the grant is re-issuable, so what must not change
            # is that a second grant cannot widen the first. What the bytes
            # actually are is settled by the digest at submit, which is the
            # check that has to be right.
            "headers": {"content-length": str(ceiling)},
            "expires_at": _from_epoch(expires),
        }

    ######################################################################
    # 15. submit
    ######################################################################

    def submit(self, session, job_id: str, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Dict[str, Any]:
        job = self.owned(session, job_id)

        if idempotency_key is not None and job["submit_idempotency_key"] == idempotency_key:
            # Already submitted under this key. The contract's answer to a
            # retried submit is the job object, which is what a fresh submit
            # returns too.
            return self.wire(job)

        if job["state"] != "awaiting_input":
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} cannot be submitted")

        digest = body.get("digest") if isinstance(body, dict) else None
        declared_bytes = body.get("bytes") if isinstance(body, dict) else None
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ProblemError(
                "invalid-request",
                detail="digest is required and is 'sha256:<hex>'")
        if not isinstance(declared_bytes, int):
            raise ProblemError("invalid-request", detail="bytes is required")

        reported = self._storage.stat_upload(job["id"])
        if reported is None:
            raise ProblemError(
                "job-state-conflict",
                detail="no upload has arrived for this job; ask for a grant and PUT to it")

        size, reported_digest = reported

        # 🔴 The order below is normative. Nothing opens the archive until the
        # digest matches, so the bytes cannot change between the check and the
        # unpack -- which is what turns the re-derivation from a TOCTOU into a
        # check.
        if reported_digest != digest or size != declared_bytes:
            self._reject(session, job, "upload-digest-mismatch")
            raise ProblemError(
                "upload-digest-mismatch",
                detail=f"storage holds {size} bytes, {reported_digest}")

        if size > self._config.limits["max_upload_bytes"]:
            self._reject(session, job, "upload-too-large")
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{size} bytes, and this server accepts at most "
                       f"{self._config.limits['max_upload_bytes']}")

        self._check_concurrent_jobs(session.user_id)

        root = self.job_root(session.user_id, job["id"])

        # The archive is the contents of one job directory, so it expands at
        # `<build root>/<design>/<jobname>/` -- which is where SiliconCompiler
        # will look for it once `option,builddir` is the job root. Both segments
        # are the DECLARED names, which were checked at create; the manifest's
        # own copies are checked against them below, so an archive cannot name
        # its way into another job's tree.
        unpacked = root / job["design"] / job["jobname"]
        try:
            archive.extract(self._storage.upload_path(job["id"]), unpacked,
                            self._config.limits)
        except archive.ArchiveRejected as rejected:
            shutil.rmtree(root, ignore_errors=True)
            self._reject(session, job, "archive-rejected")
            raise ProblemError("archive-rejected", violation=rejected.violation,
                               detail=rejected.detail) from None

        self._storage.discard_upload(job["id"])

        derived = self._derive(session, job, root)
        plan = self._resolve_images(session, job, derived)
        manifest = self._normalize(session, job, root, derived, plan)

        try:
            # The job's own root, so the batch script and the run's stdout land
            # beside what the run produced and go away with it when the job is
            # deleted.
            scheduler_job_id = self._dispatcher.submit(job["id"], root, manifest)
        except DispatchError as e:
            self._reject(session, job, "run-failed")
            raise ProblemError(
                "not-ready",
                detail=f"this server could not hand the job to its scheduler: {e}") from None

        try:
            self._record_submission(job, derived, digest, size, idempotency_key,
                                    scheduler_job_id, plan)
        except sqlite3.IntegrityError:
            # The only thing here that can collide is the submit key, and the
            # index that catches it is per user. Reusing one across two jobs is
            # the caller having reused a key they should have rotated, not a
            # fault in this server.
            raise ProblemError(
                "idempotency-key-reuse",
                detail="this Idempotency-Key was used to submit a different "
                       "job") from None

        logger.info(f"submitted {job['id']} as {scheduler_job_id}")
        return self.wire(self._row(job["id"]))

    def _resolve_images(self, session, job, derived):
        '''Which container every node of this job runs in.

        🔴 Before the dispatcher is called and after the archive is open, which
        is the only place both facts are in hand: the flow's real node list
        comes from the manifest, and nothing may be handed to the cluster that
        this server cannot place. A node whose tool this deployment tracks and
        has no image for fails the WHOLE submit here, rather than queueing and
        dying on node thirty-one with the cluster already paid for.

        ⚠️ Skipped entirely where the deployment runs no containers, and that
        answer is NULL rather than a default image -- `job_nodes.image_id` is
        *what that node actually ran in*, so writing one for a node that ran on
        the host would be a record of something that did not happen.
        '''
        if not self._config["containers"]:
            return images.Plan(None, {node: None for node in derived["nodes"]}, {})

        declared = (json.loads(job["descriptor"]) or {}).get("versions") or {}

        try:
            return images.plan_for_job(self._store, declared, derived["node_tools"])
        except ProblemError:
            self._reject(session, job, "unsatisfiable-request")
            raise

    def _record_submission(self, job, derived, digest, size, idempotency_key,
                           scheduler_job_id, plan) -> None:
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET manifest_flow = ?, manifest_nodes = ?, "
                "  manifest_tools = ?, manifest_pdk = ?, upload_digest = ?, "
                "  upload_bytes = ?, submit_idempotency_key = ?, "
                "  scheduler_job_id = ?, image_id = ?, submitted_at = ? "
                "WHERE id = ?",
                (derived["flow"], len(derived["nodes"]),
                 json.dumps(derived["tools"]), derived["pdk"], digest, size,
                 idempotency_key, scheduler_job_id, plan.job, now(), job["id"]))

            for step, index in derived["nodes"]:
                self._store.execute(
                    'INSERT INTO job_nodes (job_id, step, "index", state, image_id) '
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (job["id"], step, index, plan.nodes.get((step, index))))
            for from_step, from_index, to_step, to_index in derived["edges"]:
                self._store.execute(
                    "INSERT INTO job_node_edges "
                    "(job_id, from_step, from_index, to_step, to_index) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (job["id"], from_step, from_index, to_step, to_index))

            self._transition(job["id"], "awaiting_input", "queued",
                             actor=job["user_id"])

    def _check_concurrent_jobs(self, user_id: str) -> None:
        active = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            "AND state IN ('queued', 'running', 'cancelling')", (user_id,))["n"]
        ceiling = self._config.limits["concurrent_jobs"]
        if active >= ceiling:
            raise ProblemError(
                "limit-exceeded", limit="concurrent_jobs",
                detail=f"{active} of your jobs are already running",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    def _derive(self, session, job, root: Path) -> Dict[str, Any]:
        '''Read the uploaded manifest and re-run every check against it.

        The descriptor said what the client believed; this is what it sent. Only
        this side is authoritative, which is why the checks run twice.
        '''
        from siliconcompiler import Project

        manifest = root / job["design"] / job["jobname"] / f"{job['design']}.pkg.json"
        if not manifest.is_file():
            self._reject(session, job, "declared-mismatch")
            raise ProblemError(
                "declared-mismatch",
                detail=f"the archive holds no {job['design']}/{job['jobname']}/"
                       f"{job['design']}.pkg.json")

        try:
            project = Project.from_manifest(filepath=str(manifest))
        except Exception as e:
            self._reject(session, job, "declared-mismatch")
            raise ProblemError(
                "declared-mismatch",
                detail=f"the uploaded manifest could not be read: {e}") from None

        if project.name != job["design"] or project.option.get_jobname() != job["jobname"]:
            self._reject(session, job, "declared-mismatch")
            raise ProblemError(
                "declared-mismatch",
                detail=f"the manifest is {project.name}/{project.option.get_jobname()} "
                       f"and the job is {job['design']}/{job['jobname']}")

        try:
            runtime = runspec.runtime_flow(project)
            nodes = list(runtime.get_nodes())
        except Exception as e:
            self._reject(session, job, "declared-mismatch")
            raise ProblemError(
                "declared-mismatch",
                detail=f"the manifest names no runnable flow: {e}") from None

        if not nodes:
            self._reject(session, job, "declared-mismatch")
            raise ProblemError("declared-mismatch",
                               detail="the manifest's flow has no nodes to run")

        if len(nodes) > self._config.limits["max_job_nodes"]:
            self._reject(session, job, "node-limit-exceeded")
            raise ProblemError(
                "node-limit-exceeded", limit="max_job_nodes",
                detail=f"{len(nodes)} nodes, and this server runs at most "
                       f"{self._config.limits['max_job_nodes']}")

        # 🔴 The software version is NOT re-derived here, and that is a
        # limitation worth stating rather than a check that was forgotten. A
        # manifest records `record,scversion` per node as each node runs, so a
        # manifest that has never run carries none -- there is nothing on this
        # side to compare against. `version-skew` is therefore decided at create
        # from the descriptor's `versions`, which is exactly the field whose
        # absence the contract says costs the whole upload.

        edges = []
        for step, index in nodes:
            for in_step, in_index in runtime.get_node_inputs(step, index):
                if (in_step, in_index) in nodes:
                    edges.append((in_step, in_index, step, index))

        node_tools = _node_tools(project.get_flow(), nodes)

        return {
            "project": project,
            "flow": project.get_flow().name,
            "nodes": nodes,
            "edges": edges,
            "node_tools": node_tools,
            "tools": sorted({tool for tool in node_tools.values() if tool}),
            "pdk": _pdk(project),
        }

    def _normalize(self, session, job, root: Path, derived, plan) -> Path:
        '''Apply the server's settings and write the manifest the run will load.

        One place, once, after the digest check and after the archive limits
        bound. The list itself is in `runspec.normalize`, which is the file both
        ends read.
        '''
        project = derived["project"]

        cache = self.cache_dir(session.user_id)
        cache.mkdir(parents=True, exist_ok=True)

        runspec.normalize(project, job["id"], root, cache,
                          images=plan.placements())

        manifest = root / job["design"] / job["jobname"] / f"{job['design']}.pkg.json"
        project.write_manifest(str(manifest))
        return manifest

    def _reject(self, session, job, error_slug: str) -> None:
        '''A refused job is `rejected` and never `failed`.

        A refused job never ran, and keeping it out of `failed` is what stops a
        run of entitlement denials reading as a run of broken designs.
        '''
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (f"{TYPE_BASE}/{error_slug}", now(), job["id"]))
            self._transition(job["id"], job["state"], "rejected",
                             actor=session.user_id, reason=error_slug)
        self._storage.discard_upload(job["id"])

    ######################################################################
    # 16, 17. list and get
    ######################################################################

    def listing(self, session, args) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        '''The caller's jobs, newest first, over a keyset cursor.

        Ordered by `(created_at, id)` descending, which is the ordering the
        partial indexes carry -- and the reason the ids are UUIDv7: the
        tiebreaker sorts the same way the timestamp does, so the cursor needs no
        second column.
        '''
        where = ["user_id = ?", "deleted_at IS NULL"]
        params: List[Any] = [session.user_id]

        if _flag(args.get("archived")):
            where.append("archived_at IS NOT NULL")
        else:
            where.append("archived_at IS NULL")

        state = args.get("state")
        if state:
            if self._store.one("SELECT 1 FROM job_states WHERE state = ?", (state,)) is None:
                raise ProblemError("invalid-request", detail=f"no such job state: {state}")
            where.append("state = ?")
            params.append(state)

        for column in ("design", "jobname"):
            value = args.get(column)
            if value:
                where.append(f"{column} = ?")
                params.append(value)

        flow = args.get("flow")
        if flow:
            where.append("manifest_flow = ?")
            params.append(flow)

        if args.get("project"):
            raise ProblemError(
                "feature-unsupported", feature="projects",
                detail="this deployment has no projects")

        cursor = args.get("cursor")
        if cursor:
            created_at, job_id = _decode_cursor(cursor)
            where.append("(created_at < ? OR (created_at = ? AND id < ?))")
            params.extend([created_at, created_at, job_id])

        limit = _limit(args.get("limit"))

        rows = self._store.all(
            f"SELECT * FROM jobs WHERE {' AND '.join(where)} "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (*params, limit + 1))

        more = len(rows) > limit
        rows = rows[:limit]

        for row in rows:
            if row["state"] not in TERMINAL_STATES:
                self.reconcile(row)

        items = [self.wire(self._row(row["id"]), nodes=False) for row in rows]
        next_cursor = _encode_cursor(rows[-1]) if more and rows else None
        return items, next_cursor

    def get(self, session, job_id: str) -> Dict[str, Any]:
        job = self.owned(session, job_id)
        if job["state"] not in TERMINAL_STATES:
            self.reconcile(job)
            job = self._row(job_id)
        return self.wire(job)

    ######################################################################
    # 18, 19. cancel and delete
    ######################################################################

    def cancel(self, session, job_id: str, reason: Optional[str]) -> Dict[str, Any]:
        job = self.owned(session, job_id)

        if reason is not None:
            if not isinstance(reason, str) or len(reason) > MAX_REASON:
                raise ProblemError(
                    "invalid-request",
                    detail=f"reason is free text of at most {MAX_REASON} characters")

        if job["state"] in TERMINAL_STATES or job["state"] == "cancelling":
            # Idempotent: the caller's intent is already satisfied.
            return self.wire(job)

        if job["scheduler_job_id"]:
            self._dispatcher.cancel(job["scheduler_job_id"])

        # A running job goes to `cancelling` and the scheduler writes the
        # terminal state; one that never started has nothing to wind down, so it
        # goes straight to `cancelled`.
        target = "cancelling" if job["state"] in ("queued", "running") else "cancelled"

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET cancel_requested_at = ? WHERE id = ?",
                (now(), job["id"]))
            if target == "cancelled":
                self._store.execute(
                    "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
            self._transition(job["id"], job["state"], target,
                             actor=session.user_id, reason=reason)

        return self.wire(self._row(job["id"]))

    def delete(self, session, job_id: str) -> None:
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            return                                      # idempotent

        if job["state"] not in TERMINAL_STATES:
            raise ProblemError(
                "job-state-conflict",
                detail="cancel this job before deleting it: 'delete it and its "
                       "data' cannot mean 'hide it and keep spending'")

        shutil.rmtree(self.job_root(job["user_id"], job["id"]), ignore_errors=True)
        self._storage.discard_upload(job["id"])
        self._storage.discard_artifacts(job["id"])

        # The row stays, with `deleted_at` set: a `deleted` state was refused
        # because it would erase whether the job had completed, failed or been
        # rejected, which is the one fact you want when somebody asks where
        # their results went.
        self._store.execute(
            "UPDATE jobs SET deleted_at = ?, deleted_by = ? WHERE id = ?",
            (now(), session.user_id, job["id"]))
        self._store.execute(
            "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
            "  delete_reason = 'the job was deleted' "
            "WHERE job_id = ? AND deleted_at IS NULL",
            (now(), session.user_id, job["id"]))

    ######################################################################
    # Reconciliation: what the run says it is doing
    ######################################################################

    def reconcile(self, job) -> None:
        '''Read the run's progress file and move the store to match.

        The run writes a file beside its manifest; nothing calls back. That is
        what lets the process running the flow and the process serving this API
        be on different machines with nothing between them but a filesystem.
        '''
        root = self.job_root(job["user_id"], job["id"])
        progress = runspec.read_progress(
            root / job["design"] / job["jobname"] / runspec.PROGRESS_FILENAME)

        if progress is None:
            # Nothing written yet. Either it has not started, or it never will.
            if job["scheduler_job_id"] and not self._alive(job):
                self._lost(job)
            return

        for key, node in (progress.get("nodes") or {}).items():
            step, _, index = key.partition("/")
            state = node.get("state", "pending")

            self._store.execute(
                'UPDATE job_nodes SET state = ?, started_at = ?, finished_at = ?, '
                '  exit_code = ? WHERE job_id = ? AND step = ? AND "index" = ?',
                (state, node.get("started_at"), node.get("finished_at"),
                 node.get("exit_code"), job["id"], step, index))

            if state in TERMINAL_NODE_STATES:
                # Indexed as the node finishes rather than as the job does, so
                # a node that is done answers /logs with its archive while the
                # rest of the flow is still running -- which is precisely the
                # moment somebody tailing it asks.
                self._index_node(job, step, index)

        reported = progress.get("state")
        started_at = progress.get("started_at")

        if job["state"] == "queued" and started_at:
            with self._store.transaction():
                self._store.execute(
                    "UPDATE jobs SET started_at = ? WHERE id = ?", (started_at, job["id"]))
                self._transition(job["id"], "queued", "running")
            job = self._row(job["id"])

        if reported in ("completed", "failed"):
            final = reported
            if job["state"] == "cancelling":
                # The cancel won the race to the scheduler; what the run managed
                # to finish before it died does not change what was asked for.
                final = "cancelled"
            self._finish(job, final, progress)
        elif reported == "running" and job["scheduler_job_id"] and not self._alive(job):
            # 🔴 Look again before declaring it lost. "The run says it is
            # going" and "the scheduler has never heard of it" are read at two
            # different moments, and a run that finished in between satisfies
            # both -- the progress file in hand is stale and the scheduler's
            # answer is fresh. Everything between the two readings widens that
            # window, and indexing a node's results is not cheap.
            #
            # A job that really is gone reads the same file twice and is still
            # `running`, which costs one stat to be sure of.
            settled = runspec.read_progress(
                self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / runspec.PROGRESS_FILENAME)

            if settled and settled.get("state") in ("completed", "failed"):
                self._finish(job, settled["state"], settled)
            else:
                self._lost(job)

    def _alive(self, job) -> bool:
        try:
            return self._dispatcher.is_alive(job["scheduler_job_id"])
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not ask the scheduler about {job['id']}: {e}")
            # Cannot tell is not the same as gone, and declaring a live job lost
            # is the more expensive mistake.
            return True

    def _lost(self, job) -> None:
        '''The scheduler no longer has it and it never said how it ended.'''
        logger.warning(f"{job['id']} is gone from the scheduler with no result")
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (f"{TYPE_BASE}/scheduler-lost", now(), job["id"]))
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled' WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped')", (job["id"],))
            self._transition(job["id"], job["state"], "failed", reason="scheduler-lost")

    def _finish(self, job, state: str, progress) -> None:
        if job["state"] == state:
            return

        # Indexed before the transition, so a job is never readable as terminal
        # with an empty listing: the first thing a client does on seeing
        # `terminal` is ask what the run produced.
        self._index(job)

        with self._store.transaction():
            if state == "failed":
                self._store.execute(
                    "UPDATE jobs SET error_type = ? WHERE id = ?",
                    (f"{TYPE_BASE}/run-failed", job["id"]))
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?",
                (progress.get("finished_at") or now(), job["id"]))
            self._transition(job["id"], job["state"], state,
                             reason=progress.get("error"))

    def _index(self, job) -> None:
        '''Turn what the run left on disk into rows.

        Never fatal: a job that ran is a job that ran, and failing to index its
        output must not make it read as failed. The listing is empty, which is
        a legal answer, and the log says why.
        '''
        try:
            artifacts.collect(self._store, self._storage, self._config, job,
                              self.job_root(job["user_id"], job["id"]))
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index the results of {job['id']}: {e}")

    def _index_node(self, job, step: str, index: str) -> None:
        """Index one node's log and bundle, as that node finishes."""
        try:
            artifacts.collect_node(
                self._store, self._storage, self._config, job,
                self.job_root(job["user_id"], job["id"]), step, index)
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index {job['id']} {step}/{index}: {e}")

    ######################################################################
    # Artifacts
    ######################################################################

    def artifacts(self, session, job_id: str, args):
        '''Endpoint 21: what this run produced, as far as this caller is
        concerned.'''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            # The job stays readable and its subresources do not.
            raise ProblemError("not-found", detail="this job's data was deleted")

        where = ["job_id = ?"]
        params: List[Any] = [job["id"]]

        kind = args.get("kind")
        if kind:
            if self._store.one("SELECT 1 FROM artifact_kinds WHERE kind = ?",
                               (kind,)) is None:
                raise ProblemError("invalid-request", detail=f"no such kind: {kind}")
            where.append("kind = ?")
            params.append(kind)

        if args.get("step"):
            where.append("step = ?")
            params.append(args["step"])
        if args.get("index"):
            where.append('"index" = ?')
            params.append(args["index"])

        cursor = args.get("cursor")
        if cursor:
            created_at, artifact_id = _decode_cursor(cursor)
            where.append("(created_at > ? OR (created_at = ? AND id > ?))")
            params.extend([created_at, created_at, artifact_id])

        limit = _limit(args.get("limit"))
        rows = self._store.all(
            f"SELECT * FROM artifacts WHERE {' AND '.join(where)} "
            "ORDER BY created_at, id LIMIT ?", (*params, limit + 1))

        more = len(rows) > limit
        rows = rows[:limit]

        items = [artifacts.wire(row) for row in rows]
        return items, (_encode_cursor(rows[-1]) if more and rows else None)

    def artifact(self, session, job_id: str, artifact_id: str):
        '''Endpoint 22's row, with the two refusals it can make.'''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        row = self._store.one(
            "SELECT * FROM artifacts WHERE id = ? AND job_id = ?",
            (artifact_id, job["id"]))
        if row is None:
            raise ProblemError("not-found", detail="no such artifact")

        if row["deleted_at"]:
            # The bytes are gone. 404 rather than 403: there is nothing to be
            # entitled to.
            raise ProblemError("not-found", detail="these bytes were deleted")

        if not artifacts.fetchable(row):
            raise ProblemError(
                "entitlement-denied", resource_kind="artifact", resource=row["kind"],
                detail="this artifact is not available to fetch")

        return row

    def node_log(self, session, job_id: str, step: str, index: str):
        '''Endpoint 20's target: the archived log for one terminal node.

        Returns ``("stream", node)`` or ``("artifact", row)`` -- the two things
        a 303 can point at. Everything else this endpoint can answer is a
        refusal, and which one depends on the node's state rather than on the
        artifact: a node that has not run has no log, and saying `not-found`
        would tell a client to stop asking.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        node = self._store.one(
            'SELECT * FROM job_nodes WHERE job_id = ? AND step = ? AND "index" = ?',
            (job["id"], step, index))
        if node is None:
            raise ProblemError("not-found", detail=f"no node {step}/{index} in this job")

        if node["state"] in ("pending", "queued", "preparing"):
            raise ProblemError(
                "not-ready", artifact_kind="logs",
                detail=f"{step}/{index} has not started",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

        if node["state"] == "running":
            if "logs.stream" not in self._config["features"]:
                # Permanent for the tail and not for the log: the archive still
                # arrives when the node finishes. A client must not retry this.
                raise ProblemError(
                    "feature-unsupported", feature="logs.stream",
                    detail="this deployment does not serve a live log; the "
                           "archived log is available once the node finishes")
            return "stream", node

        self._index_node(job, step, index)

        row = self._store.one(
            "SELECT * FROM artifacts WHERE job_id = ? AND step = ? "
            'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
            "ORDER BY created_at LIMIT 1", (job["id"], step, index))

        if row is None:
            if job["state"] not in TERMINAL_STATES:
                # The node is over and the job is not, so the archive may still
                # be on its way. 🔴 Transient rather than `not-found`: a 404
                # tells a client to stop asking about a log that is about to
                # exist.
                raise ProblemError(
                    "not-ready", artifact_kind="logs",
                    detail=f"the log for {step}/{index} has not been archived yet",
                    headers={"Retry-After":
                             str(self._config["poll_interval_seconds"])})
            raise ProblemError(
                "not-found", detail=f"no log was kept for {step}/{index}")

        return "artifact", row

    def node_log_path(self, job, step: str, index: str):
        '''Where the bytes a tail reads are.'''
        return (self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / step / index / f"sc_{step}_{index}.log")

    def node_state(self, job_id: str, step: str, index: str):
        '''What this node is doing NOW.

        Read fresh every time rather than captured, because a stream asks over
        and over across the hours it may be open.
        '''
        row = self._store.one(
            'SELECT state FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        return row["state"] if row else None

    def node_log_artifact(self, job_id: str, step: str, index: str):
        '''The archived log's id, indexing it first if it is not there yet.

        🔴 Called as a tail reaches the end of a node. The alternative is
        waiting for the next poll to reconcile, which leaves a window where the
        stream has said `terminal` and the archive it names does not exist --
        so a client that follows the `end` event straight to `/logs` is told
        there is no log for a node whose log it has just finished reading.
        '''
        job = self._row(job_id)
        if job is not None:
            self._index_node(job, step, index)

        row = self._store.one(
            "SELECT id FROM artifacts WHERE job_id = ? AND step = ? "
            'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
            "ORDER BY created_at LIMIT 1", (job_id, step, index))
        return row["id"] if row else None

    ######################################################################
    # Rows, and the objects they become
    ######################################################################

    def owned(self, session, job_id: str):
        '''A job, or a 404 that does not say whether it exists.

        The predicate is the whole point of the identity work: a stranger
        holding an id is not the owner. A 403 would confirm the id belongs to
        somebody.
        '''
        row = self._store.one(
            "SELECT * FROM jobs WHERE id = ? AND user_id = ?", (job_id, session.user_id))
        if row is None:
            raise ProblemError("not-found", detail="no such job")
        return row

    def _row(self, job_id: str):
        return self._store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def _transition(self, job_id: str, from_state: Optional[str], to_state: str,
                    actor: Optional[str] = None, reason: Optional[str] = None) -> None:
        self._store.execute(
            "UPDATE jobs SET state = ?, state_changed_at = ? WHERE id = ?",
            (to_state, now(), job_id))
        self._store.execute(
            "INSERT INTO job_state_transitions "
            "(job_id, from_state, to_state, actor_user_id, reason) VALUES (?, ?, ?, ?, ?)",
            (job_id, from_state, to_state, actor, reason))

    def wire(self, job, nodes: bool = True) -> Dict[str, Any]:
        '''The job object, as §17 publishes it.'''
        body = {
            "id": job["id"],
            "state": job["state"],
            # Published rather than derivable on purpose. The rule is read
            # `terminal`, do not switch on the name -- which is what makes an
            # eleventh state additive instead of breaking.
            "terminal": job["state"] in TERMINAL_STATES,
            "state_changed_at": job["state_changed_at"],
            "design": job["design"],
            "jobname": job["jobname"],
            "flow": job["manifest_flow"],
            # The user id rather than a display name: it is what GET /v1/me
            # returns, so a client can compare the two. Nothing here verifies
            # who anybody is, and a name that looked like an email would suggest
            # otherwise.
            "owner": job["user_id"],
            "project": None,
            "created_at": job["created_at"],
            "submitted_at": job["submitted_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
            "archived_at": job["archived_at"],
            "deleted_at": job["deleted_at"],
            "error": _error(job["error_type"]),
        }
        # No `web_url`: absent, never null, where the deployment serves no web
        # UI. A null would claim there is a portal and this job has no page.

        rows = self._store.all(
            'SELECT step, "index", state, started_at, finished_at, exit_code, error_type '
            'FROM job_nodes WHERE job_id = ? ORDER BY step, "index"', (job["id"],))

        if nodes:
            body["nodes"] = [{
                "step": row["step"],
                "index": row["index"],
                "state": row["state"],
                "terminal": row["state"] in TERMINAL_NODE_STATES,
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "exit_code": row["exit_code"],
                "error_type": row["error_type"],
            } for row in rows]

        body["progress"] = {
            "total_count": len(rows),
            "completed_count": sum(1 for row in rows if row["state"] == "completed"),
            "failed_count": sum(1 for row in rows if row["state"] == "failed"),
        }
        return body


######################################################################
# Small things, kept out of the class
######################################################################

def _name(value, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProblemError("invalid-request", detail=f"{field} is required")
    if len(value) > MAX_NAME or not _NAME_RE.match(value):
        # Both of these become a path segment under the job's own root, so the
        # check is not cosmetic: it is the reason a manifest cannot name its way
        # out of the directory the server gave it.
        raise ProblemError(
            "invalid-request",
            detail=f"{field} must be at most {MAX_NAME} characters of "
                   "letters, digits, '.', '_' and '-'")
    return value


def _opaque(value, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ProblemError("invalid-request",
                           detail=f"{field} is an opaque string of at most 200 characters")
    return value


def _node_tools(flow, nodes) -> Dict[Tuple[str, str], Optional[str]]:
    '''Which tool each node runs, which is what the image resolution needs.

    🔴 Per node rather than a set for the whole flow, because submit resolves N
    images and not one: an `import` node needing nothing but Python has no
    business pulling a twelve-gigabyte OpenROAD image, and the only thing that
    can tell them apart is which tool each node names.

    Derived from the task classes the flowgraph names rather than from the
    manifest's `tool` section, which is written during a run and so is empty in
    anything a client uploads. A node whose task will not load names no tool,
    which resolves to the job's own image -- the safe direction, since that is
    what a node needing nothing gets.
    '''
    tools: Dict[Tuple[str, str], Optional[str]] = {}
    for step, index in nodes:
        try:
            tools[(step, index)] = flow.get_task_module(step, index)().tool()
        except Exception:                                       # noqa: BLE001
            tools[(step, index)] = None
    return tools


def _pdk(project) -> str:
    '''The PDK this run needs, or the literal 'none'.

    'none' is a value rather than a NULL: a flow that needs no PDK has resolved
    its PDK requirement, and the column's CHECK on admitted jobs has to be able
    to tell that apart from one that has not been resolved yet.
    '''
    try:
        pdk = project.get("asic", "pdk")
    except Exception:                                           # noqa: BLE001
        pdk = None
    return pdk or "none"


def _error(error_type: Optional[str]) -> Optional[Dict[str, Any]]:
    if not error_type:
        return None
    slug = error_type.rsplit("/", 1)[-1]
    title = ERRORS[slug].title if slug in ERRORS else "The job failed"
    return {"type": error_type, "title": title}


def _flag(value) -> bool:
    return str(value).lower() in ("1", "true", "yes")


def _limit(value) -> int:
    if value is None:
        return 50
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise ProblemError("invalid-request", detail="limit must be a number") from None
    return max(1, min(limit, 200))


def _encode_cursor(row) -> str:
    raw = f"{row['created_at']}|{row['id']}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> Tuple[str, str]:
    '''Opaque on the wire, and refused rather than guessed at.

    A cursor is only ever taken from a `Link` header, so one that does not
    decode was made up -- and continuing from a made-up position would silently
    skip rows.
    '''
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, _, job_id = base64.urlsafe_b64decode(padded).decode().partition("|")
    except Exception:                                           # noqa: BLE001
        raise ProblemError("invalid-cursor") from None

    if not created_at or not job_id:
        raise ProblemError("invalid-cursor")
    return created_at, job_id


def _epoch() -> float:
    import time
    return time.time()


def _from_epoch(value: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(value, timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _retention(days: int) -> str:
    from datetime import datetime, timedelta, timezone
    when = datetime.now(timezone.utc) + timedelta(days=days)
    return when.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
