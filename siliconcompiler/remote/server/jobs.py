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
import hashlib
import json
import logging
import re
import shutil
import sqlite3
import warnings

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from siliconcompiler.schema.baseschema import SchemaVersionWarning

from siliconcompiler.remote import owners, units
from siliconcompiler.remote.server import archive, artifacts, confine, images, runspec
from siliconcompiler.remote.server.dispatch import DispatchError
from siliconcompiler.remote.server.errors import (
    bound, ERRORS, ProblemError, TYPE_BASE)
from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now
from siliconcompiler.remote.server.storage import grant_seconds

__all__ = ["JobService", "TERMINAL_STATES", "REUSABLE_STATES"]


logger = logging.getLogger("sc-server")


# Published on the job object, so a client reads `terminal` and never switches
# on the name. The set has grown twice already.
TERMINAL_STATES = frozenset(
    ("completed", "failed", "cancelled", "rejected", "abandoned"))
TERMINAL_NODE_STATES = frozenset(("completed", "failed", "skipped", "cancelled"))

# 🔴 How often ONE process will ask the scheduler about ONE job, at most.
# Deliberately decoupled from `poll_interval_seconds`: reading a job is a local
# SQLite read and a stat, and can be answered as fast as anybody asks, while
# `squeue` is one or more RPCs into slurmctld and is the only part that leaves
# the machine. Without this, shortening the poll interval multiplied scheduler
# load by the same factor -- the load `--max-connections` exists to throttle.
SCHEDULER_QUERY_FLOOR = 5

# Job reuse returns a result the hash determines and never a refusal it does
# not: `rejected` is an entitlement decision about a person at a moment, and
# `cancelled` and `abandoned` are somebody having stopped.
REUSABLE_STATES = ("completed", "failed")

# What a job-stream request is told for each capability the deployment lacks,
# broadest first.
_WITHOUT = {
    "logs": "this deployment does not serve logs over the API; they are on "
            "the web portal",
    "logs.stream": "this deployment does not serve a live log; each node's "
                   "archived log is available once it finishes",
    "logs.stream.job": "this deployment does not merge a job's logs into one "
                       "stream; follow each running node instead",
}

# The two surfaces a caller reaches a job through. They disagree about exactly
# two things -- `max_download_bytes` and `api_fetchable_kinds` -- and both are
# decided from this one value.
SURFACES = ("api", "portal")

# SiliconCompiler's own tasks -- nop, join, minimum, maximum, verify. They run
# in the framework's process, so they name no tool a deployment could install.

# Long enough for any real design or job name and short enough that the column,
# the path and the log line all stay sane.
MAX_NAME = 100
MAX_REASON = 500

# `design` and `jobname` become path segments under the job's own root, so they
# are checked rather than trusted. The manifest's own copies are checked again
# at submit against the same rule -- an upload is the other end of this.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _as_data(method):
    '''🔴 Every manifest ``method`` reads, it reads as data (contract §1): a
    class or task module the manifest names is looked up among what this
    installation provides, and never imported -- for the whole call, since the
    project it derives is used throughout.'''
    import functools

    from siliconcompiler.remote.server import schemaclasses

    @functools.wraps(method)
    def wrapped(*args, **kwargs):
        with schemaclasses.reading():
            return method(*args, **kwargs)
    return wrapped


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

        # Per job, the last time this process asked the scheduler anything.
        self._asked = {}

        # This server's own copies of remote sources, fetched only from the
        # allowlist, and what answers "can you supply this" by identity.
        import threading

        from siliconcompiler.remote.server import allowlist
        from siliconcompiler.remote.server.sources import SourceStore

        self._sources = SourceStore(
            self._datadir,
            [allowlist.parse(entry) for entry in (config["fetch_allowlist"] or [])])
        self._supply = _Supply(config, self._sources)

        # The jobs whose sources are being fetched in this process, so a
        # restart can tell one still in hand from one it has to pick up again.
        self._preparing = set()
        self._preparing_lock = threading.Lock()

        # One environment build per key at a time in this process: two jobs
        # asking for the same set wait for one build, and the second reuses it.
        self._building: Dict[str, Any] = {}
        self._building_lock = threading.Lock()
        # How a build is waited on -- `envbuild.wait_for`'s pacing.
        self._build_wait: Dict[str, float] = {}

    ######################################################################
    # Where a user's work lives
    ######################################################################

    def user_root(self, user_id: str) -> Path:
        return self._datadir / "users" / user_id

    def builds_root(self, user_id: str) -> Path:
        return self.user_root(user_id) / "builds"

    def cache_dir(self, user_id: str) -> Path:
        return self.user_root(user_id) / "cache"

    def container_mounts(self):
        '''What every container this deployment runs must be able to see.

        The data directory always, because every path in a job's manifest is
        under it, plus whatever the cluster needs named -- the munge socket and
        slurm.conf on Slurm, since a framework image submits the nodes of the
        flow it is driving.
        '''
        # 🔴 Supplied roots are READ-ONLY in the job: the held copies of remote
        # sources, bound over their place inside the data directory, and every
        # private root the operator maps. A job reads what it is supplied and
        # can change none of it -- the next job gets the same copy.
        supplied = [(str(self._datadir / "sources"), "ro")] + [
            (str(root), "ro")
            for roots in (self._config["private_dataroots"] or {}).values()
            for root in roots.values()]
        return [str(self._datadir)] + [
            str(path) for path in (self._config["container_mounts"] or [])] + supplied

    def bundles_root(self) -> Path:
        '''Where unpacked container images live.

        🔴 Beside the store rather than under a user's tree, which is the one
        place in this layout that is deliberately NOT per user. A bundle is a
        read-only root filesystem identical for everybody who runs that digest,
        so per-user copies would buy nothing and cost a copy of every tool image
        per user -- the one number decision 3 accepted for the cache and would
        not accept twice.
        '''
        return self._datadir / "images"

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
        '''Returns the job object and the status it should be served with.

        The top-level members are authoritative; everything under `descriptor`
        is advisory, re-derived at submit, and stored as `jobs.descriptor`.
        🔴 Strict, like every request body: an unknown member is refused, never
        ignored.
        '''
        if not isinstance(body, dict):
            raise ProblemError("invalid-request", detail="the body must be a JSON object")
        _only(body, CREATE_MEMBERS, "the create body")

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

        descriptor = body.get("descriptor")
        if descriptor is None:
            descriptor = {}
        if not isinstance(descriptor, dict):
            raise ProblemError("invalid-request", detail="descriptor must be an object")
        _only(descriptor, DESCRIPTOR_MEMBERS, "descriptor")
        # 🔴 Top level, beside `design` and `jobname` (surface D160, job-reuse
        # D15): `descriptor` holds what submit re-derives, and nothing
        # recomputes this. Validated always; USED only where this deployment
        # advertises `jobs.reuse` -- elsewhere it is recorded and ignored, and
        # create is always a 201.
        run_hash = _run_hash(body.get("run_hash"))
        reuses = "jobs.reuse" in (self._config["features"] or ())

        # 🔴 Credentials out of every source URL before anything is compared,
        # stored or logged -- the descriptor is kept whole in `jobs.descriptor`.
        declared = _declared_sources(descriptor)
        if declared is not None:
            descriptor = dict(descriptor, sources=declared)
        requires = requirements(descriptor)
        self._check_needs(descriptor)

        if idempotency_key is not None:
            existing = self._store.one(
                "SELECT * FROM jobs WHERE user_id = ? AND idempotency_key = ?",
                (session.user_id, idempotency_key))
            if existing is not None:
                # The same key with a different body is the caller having reused
                # a key they should have rotated. Returning the first job would
                # answer a question they did not ask.
                if (existing["design"], existing["jobname"], existing["run_hash"],
                        json.loads(existing["descriptor"])) != (design, jobname, run_hash,
                                                                descriptor):
                    raise ProblemError(
                        "idempotency-key-reuse",
                        detail="this Idempotency-Key was used for a different request")
                return self.wire(existing), 200

        # 🔴 Before the reuse lookup, because the answer is part of what the
        # lookup is keyed on -- and before the upload, which is the whole point
        # of resolving here at all.
        identity = self._identity(run_hash, requires) if reuses else None

        if identity:
            hit = self._reuse(session.user_id, identity)
            if hit is not None:
                # 200 rather than 201: a 201 carrying an old job's id is
                # indistinguishable from a new one. The body is the job object
                # either way, so a client that ignores the status is still
                # correct.
                logger.info(f"run_hash hit for {session.user_id}: {hit['id']}")
                return self.wire(hit), 200

        self._check_pending_uploads(session.user_id)
        self._check_descriptor(descriptor, requires)

        asked = self._look_up(declared) if declared is not None else None

        job_id = str(uuid7())
        device_id = session.device_id

        with self._store.transaction():
            self._store.execute(
                "INSERT INTO jobs (id, user_id, device_id, state, design, jobname, "
                "                  descriptor, idempotency_key, run_hash, "
                "                  job_identity, retention_until, upload_sources) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, session.user_id, device_id, design, jobname,
                 json.dumps(descriptor), idempotency_key, run_hash, identity,
                 _retention(self._config.limits["job_retention_days"]),
                 json.dumps(asked) if asked else None))
            self._transition(job_id, None, "created", actor=session.user_id)

        # The job object, in `created`: `upload_sources` is on it where the
        # server is asking, and absent where there is nothing to send.
        return self.wire(self._row(job_id)), 201

    def _check_needs(self, descriptor) -> None:
        '''🔴 `needs`: every feature the job relies on must be one this server
        advertises -- refused at create, naming the first it lacks, rather than
        at submit after the upload. A string it does not know is refused the
        same way.'''
        needs = descriptor.get("needs")
        if needs is None:
            return
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            raise ProblemError("invalid-request", detail="needs is a list of feature strings")
        advertised = set(self._config["features"] or ())
        for feature in needs:
            if feature not in advertised:
                raise ProblemError(
                    "feature-unsupported", feature=feature,
                    detail=f"this job needs {feature}, which this deployment does "
                           "not offer")

    def _look_up(self, declared) -> List[Dict[str, Any]]:
        '''What of the declared sources this server cannot supply: a LOOKUP,
        never a fetch (D124).

        =================================  =================================
        A source that is                   Answer
        =================================  =================================
        private, and not in the map        `resource-unavailable`, refused
        held, or in the private map        supplied -- not listed
        an installed package held here     supplied -- not listed
        on the allowlist, not held         assumed fetchable -- not listed
        anything else                      listed in `upload_sources`
        =================================  =================================

        🔴 No network: probing hundreds of dataroots against a slow git host
        put latency inside a request behind gateway timeouts, and turned one
        `POST` into hundreds of outbound requests.
        '''
        asked = []
        for item in declared:
            kind, name, dataroot = item["kind"], item["name"], item["dataroot"]
            if item["private"]:
                if kind == "design" or not self._supply.private_root(name, dataroot):
                    raise ProblemError(
                        "resource-unavailable", resource_kind=kind, resource=name,
                        detail=f"a private {kind} dataroot this server has no copy "
                               "of; it is never uploaded, so it cannot be sent")
                continue
            source, ref = item.get("source"), item.get("ref")
            if self._supply.held(source, ref) or self._supply.allowlisted(source, ref):
                continue
            if source and source.startswith("python://") and \
                    self._supply.package(source[len("python://"):].split("/")[0]):
                continue
            asked.append({"kind": kind, "name": name, "dataroot": dataroot})
        return asked

    def _identity(self, run_hash: Optional[str], requires) -> Optional[str]:
        '''``H(client hash || the digests it resolved to)``, or None.

        🔴 **The client's hash alone is not the job's identity, and treating it
        as one hands back a result produced by different code.** The client
        hashes the work; this server chooses what runs it. Folding in the
        digests means two runs asking for the same thing but resolved to
        different images are correctly different jobs -- and re-registering an
        image invalidates reuse exactly when it should, because a new digest is
        precisely *the code changed*.

        🔴 **Computed from the descriptor and the registry only.** No uploaded
        bytes are involved, which is what lets this happen at create and save
        the upload. It is therefore the same value at create and at submit for
        the same declared versions, and it is written once.

        ⚠️ None where the client sent no hash, which is every SiliconCompiler
        client today: what SC should hash is a decision that lives elsewhere,
        and this half is proven by the conformance fixtures rather than left as
        dead code.
        '''
        if not run_hash:
            return None

        digests: List[str] = []
        if self._config["containers"]:
            digests = images.digests_for(self._store, requires)

        payload = "\n".join([run_hash, *sorted(digests)])
        return hashlib.sha256(payload.encode()).hexdigest()

    def _reuse(self, user_id: str, identity: str):
        '''The caller's own newest job with this identity, if it may be handed
        back.

        🔴 Owner-scoped, and that is the whole safety argument. Half of the
        identity is the client's own hash, which this server never recomputes
        or normalises, so a wrong one hands a user their own stale job --
        confusing, and not a disclosure. An archived job is excluded, which is
        how a person says *stop handing me that result* without an endpoint for
        it.

        🔴 And a candidate is checked against the registry as it is NOW --
        see `_still_current`. Matching is not enough: an image the job ran in
        may have been superseded since, and handing back a result produced by
        code that is gone is the thing reuse must not do.
        '''
        placeholders = ", ".join("?" * len(REUSABLE_STATES))
        candidate = self._store.one(
            "SELECT * FROM jobs WHERE user_id = ? AND job_identity = ? "
            f"  AND state IN ({placeholders}) "
            "  AND deleted_at IS NULL AND archived_at IS NULL "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (user_id, identity, *REUSABLE_STATES))

        if candidate is None or self._still_current(candidate):
            return candidate

        logger.info(f"{candidate['id']} matches, and the images it ran in have "
                    "been superseded; running it again")
        return None

    def _still_current(self, job) -> bool:
        '''Whether the images this job actually ran in are still live.

        🔴 **What closes the gap the identity cannot.** The identity folds in
        the digests the DECLARED versions resolve to, because that is all there
        is at create -- the per-node tool images need the flow, which needs the
        manifest, which needs the upload the check exists to avoid. So
        re-registering an image that only ever served a TOOL leaves the
        identity unchanged, and the candidate would be handed back although the
        code that produced it is gone.

        ✅ A finished job records what its nodes RAN IN, so the question can be
        asked the other way round: are those images still live? It is
        computable at create, deterministic, and it invalidates only the jobs
        whose images actually changed.

        ⚠️ A job that ran in no image -- a deployment that runs on the host --
        has nothing to check and stays reusable.
        '''
        rows = self._store.all(
            "SELECT DISTINCT image_id FROM job_nodes "
            "WHERE job_id = ? AND image_id IS NOT NULL", (job["id"],))

        ran_in = {row["image_id"] for row in rows}
        if job["image_id"]:
            ran_in.add(job["image_id"])
        if not ran_in:
            return True

        live = {row["id"] for row in self._store.all(
            "SELECT id FROM images WHERE retired_at IS NULL")}
        return ran_in <= live

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

    def _check_descriptor(self, descriptor: Dict[str, Any], requires) -> None:
        '''The early reject, on whatever is present.

        Client-asserted, so this is a hint and not a boundary -- every value is
        re-derived at submit. It exists to save an upload, and it never refuses
        a descriptor for being sparse: a missing field skips the check it would
        have answered.
        '''
        limits = self._config.limits

        flow = descriptor.get("flow")
        if flow is not None:
            if not isinstance(flow, dict):
                raise ProblemError("invalid-request", detail="descriptor.flow must be an object")
            _only(flow, ("name", "nodes"), "descriptor.flow")
        flow = flow or {}
        if isinstance(flow.get("nodes"), int):
            if flow["nodes"] > limits["max_job_nodes"]:
                raise ProblemError(
                    "node-limit-exceeded", limit="max_job_nodes",
                    detail=f"{flow['nodes']} nodes, and this server runs at most "
                           f"{limits['max_job_nodes']}")

        # The early entitlement check: the tools `requires` names and the
        # resources `sources` names, against what nobody here may use.
        # Re-derived at submit, where the manifest is the answer.
        wanted = [(item["kind"], item["name"]) for item in descriptor.get("sources") or []
                  if item["kind"] in owners.RESOURCE_KINDS]
        wanted += [("tool", name) for name in sorted(requires["tools"])]
        for kind, name in wanted:
            if self._config.denied(kind, name):
                raise ProblemError(
                    "entitlement-denied", resource_kind=kind, resource=name,
                    detail=f"this job names a {kind} this deployment does not allow")

        self._check_versions(requires)

        # And whether ONE image holds the python set together, which only the
        # join can say -- where nodes run in containers, and only for a
        # descriptor that names any: a sparse one skips the check.
        if self._config["containers"] and requires.get("python"):
            images.digests_for(self._store, requires)

    def _check_versions(self, requires: Dict[str, Dict[str, Any]]) -> None:
        '''Refuse a client this deployment cannot run.

        The cheap check, before the upload -- but only the cheap one: a client
        that declares nothing reaches the binding check at submit instead,
        after the whole archive has moved.

        🔴 **A requirement is a PEP 440 specifier and the SERVER resolves it.**
        A client cannot: `GET /v1`'s `software` is flat per name within a
        bucket while the image join is over combinations, so a client resolving
        each requirement on its own can name a set no single image holds --
        every version published, every one satisfiable, and nothing to run them
        in. ⚠️ A bare version means `==`, which is what every client sent
        before the wire carried ranges.

        ⚠️ **This is the per-name check and not the resolution.** It answers
        *does this server have anything matching* for each name on its own;
        *does ONE image hold all of them* is `digests_for`, which runs beside
        it at create. Both are needed: this one gives a name-specific
        `version-skew` where the join could only say the combination failed.

        🔴 **A name that is present and reports no version gets its own
        answer.** A tool recorded from its image's publish date is in
        `software`, which has nowhere to carry the mark, so a client's
        preflight says yes and this says no. Telling them *no image matches*
        would send them looking for a version that is already installed; the
        true answer is that nothing here can be matched against a range.
        '''
        from siliconcompiler.remote.server.routes.meta import (
            advertised_reported, advertised_software)

        available = advertised_software(self._store, self._config)
        reported = advertised_reported(self._store, self._config)

        for bucket, wanted in requires.items():
            here = available.get(bucket) or {}
            said = reported.get(bucket) or {}

            for name, asked in wanted.items():
                if name not in here:
                    continue

                spec = images.specifiers(asked)
                if any(images.matches(version, "reported", spec)
                       for version in said.get(name, ())):
                    continue

                # 🔴 `version-skew` is the client's SiliconCompiler, which
                # cannot run here; any other name is software no image holds
                # (surface §7), whose answer names what is available.
                if here[name] and not said.get(name):
                    detail = (f"this server has {name}, and reports no version for "
                              "it -- so nothing here can be matched against a "
                              f"version requirement. Ask for {name} without one")
                else:
                    detail = (f"this server runs {name} {', '.join(here[name])}, "
                              f"and you asked for {asked}")
                if name == images.PRIMARY:
                    raise ProblemError("version-skew", detail=detail)
                raise ProblemError(
                    "software-unavailable", reason="unavailable", detail=detail,
                    unresolved=[{"name": name, "requirement": list(asked or ()),
                                 "available": sorted(said.get(name, ()))}])

    ######################################################################
    # 14. upload-grant
    ######################################################################

    def grant(self, session, job_id: str, url_root: str,
              body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        '''Endpoint 14: a grant for the archive about to be uploaded.

        🔴 **`bytes` is REQUIRED, and the first grant for each archive fixes
        it** (D125); a re-issue must repeat it. The size used to come from
        `resources.upload_bytes` at create, and the create response can then
        ask for more -- `upload_sources` -- so the `PUT` failed its signature.
        `max_upload_bytes` bounds a job's archives together.
        '''
        job = self.owned(session, job_id)

        if job["state"] not in ("created", "awaiting_input"):
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} takes no upload")

        _only(body or {}, ("bytes",), "the grant request")
        size = (body or {}).get("bytes") if isinstance(body, dict) else None
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ProblemError("invalid-request",
                               detail="bytes is required: the size of the archive to upload")

        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}")

        if job["grant_bytes"] is not None and job["grant_bytes"] != size:
            # A re-issue cannot widen -- or narrow -- what the first grant bound.
            raise ProblemError(
                "job-state-conflict",
                detail=f"this archive's first grant fixed its size at "
                       f"{job['grant_bytes']} bytes; a re-issue must repeat it")

        expires = int(_epoch()) + grant_seconds(self._config.limits["max_upload_bytes"])
        signature = self._storage.sign_upload(job["id"], size, expires)
        ceiling = size

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_key = ?, upload_location_id = ?, grant_bytes = ?, "
                "  upload_grant_expires_at = ?, upload_revoked_at = NULL WHERE id = ?",
                (job["id"], self._config["storage_location_id"], size,
                 _from_epoch(expires), job["id"]))
            if job["state"] == "created":
                self._transition(job["id"], "created", "awaiting_input",
                                 actor=session.user_id)

        url = (f"{url_root.rstrip('/')}/storage/upload/{job['id']}"
               f"?max_bytes={ceiling}&expires={expires}&sig={signature}")

        return {
            "method": "PUT",
            "url": url,
            # The size the first grant of this archive fixed, and the
            # signature carries the same number, so a re-issue cannot widen it.
            # What the bytes actually are is settled by the digest at submit.
            "headers": {"content-length": str(ceiling)},
            "expires_at": _from_epoch(expires),
        }

    ######################################################################
    # 15. submit
    ######################################################################

    @_as_data
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

        # 🔴 The digest and nothing else: the grant fixed the size and storage
        # enforced it on the PUT, so a `bytes` here would be a second copy --
        # and strict validation refuses it.
        _only(body if isinstance(body, dict) else {}, ("digest",), "the submit request")
        digest = body.get("digest") if isinstance(body, dict) else None
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ProblemError(
                "invalid-request",
                detail="digest is required and is 'sha256:<hex>'")

        reported = self._storage.stat_upload(job["id"])
        if reported is None:
            raise ProblemError(
                "job-state-conflict",
                detail="no upload has arrived for this job; ask for a grant and PUT to it")

        size, reported_digest = reported

        # Before anything is kept: `limit-exceeded` here is retried, and the
        # retry needs the upload still where the grant put it.
        self._check_concurrent_jobs(session.user_id)

        # 🔴 Kept from here on, as its own `input`, whatever happens next: every
        # upload the job took can be looked at afterwards -- a refused one most
        # of all (surface D133). Moved, so nothing is stored twice, and under
        # the hash storage reports for the bytes, which is what they are.
        with self._store.transaction():
            upload_id = artifacts.record_upload(
                self._store, self._storage, self._config, job,
                self._storage.upload_path(job["id"]), reported_digest, size)
        # Only what is left of it: an interrupted PUT's partial file.
        self._storage.discard_upload(job["id"])
        kept = self._storage.artifact_path(f"{job['id']}/{upload_id}")

        # 🔴 The order below is normative. Nothing opens the archive until the
        # digest matches, so the bytes cannot change between the check and the
        # unpack -- which is what turns the re-derivation from a TOCTOU into a
        # check.
        if reported_digest != digest:
            raise self._refuse(session, job, ProblemError(
                "upload-digest-mismatch",
                detail=f"storage holds {size} bytes, {reported_digest}"))

        # Every archive of the job together (D125): a follow-up cannot carry
        # what the first was refused for being too large.
        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise self._refuse(session, job, ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}"))

        root = self.job_root(session.user_id, job["id"])

        # The archive is the contents of one job directory, so it expands at
        # `<build root>/<design>/<jobname>/` -- which is where SiliconCompiler
        # will look for it once `option,builddir` is the job root. Both segments
        # are the DECLARED names, which were checked at create; the manifest's
        # own copies are checked against them below, so an archive cannot name
        # its way into another job's tree.
        unpacked = root / job["design"] / job["jobname"]
        follow_up = job["archives_bytes"] > 0

        # 🔴 A follow-up archive may hold only the dataroots that were asked
        # for (D124), so it cannot replace what the first archive carried after
        # the server checked it.
        allowed = self._requested_members(job, root) if follow_up else None
        try:
            archive.extract(kept, unpacked, self._config.limits, allowed=allowed)
        except archive.ArchiveRejected as rejected:
            if not follow_up:
                shutil.rmtree(root, ignore_errors=True)
            # Kept, and never opened again: see `artifacts.UNOPENED`.
            raise self._refuse(session, job, ProblemError(
                "archive-rejected", violation=rejected.violation,
                detail=rejected.detail)) from None

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET archives_bytes = archives_bytes + ?, grant_bytes = NULL, "
                "  upload_digest = ?, upload_bytes = ? WHERE id = ?",
                (size, digest, size, job["id"]))
        job = self._row(job["id"])

        # Re-derived over the union of every archive, never from `sources`.
        derived = self._derive(session, job, root)
        self._check_environments(session, job, derived, unpacked)
        self._check_denied(session, job, derived)
        entries = self._account(session, job, derived, unpacked)

        asked = [entry for entry in entries if entry.status == owners.ASK]
        self._check_owed(session, job, derived, asked)

        # 🔴 A job with something to get ready stages first (surface D130):
        # fetching its sources, asking for what it cannot fetch, and building
        # its nodes' Python environments are where it can still be sent back or
        # refused, so they happen BEFORE `queued`, which then only moves
        # forward. One with nothing to stage queues at once.
        #
        # 🔴 **The `202` says `staging` or `queued`, never `awaiting_input`**
        # (surface D151): something the client can send and has not goes back
        # through the one backwards edge, from `staging`, like a source that
        # could not be fetched.
        stages = any(entry.status in (owners.FETCH, owners.ASK) for entry in entries) \
            or bool(self._environments(job, derived))
        try:
            with self._store.transaction():
                # The PDK with it: an admitted job has a resolved one.
                self._store.execute(
                    "UPDATE jobs SET upload_sources = NULL, submit_idempotency_key = ?, "
                    "  manifest_pdk = ? WHERE id = ?",
                    (idempotency_key, derived["pdk"], job["id"]))
                self._transition(job["id"], "awaiting_input",
                                 "staging" if stages else "queued",
                                 actor=session.user_id)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" not in str(e):
                raise
            # The only thing here that can collide is the submit key, and the
            # index that catches it is per user. Reusing one across two jobs is
            # the caller having reused a key they should have rotated, not a
            # fault in this server.
            raise ProblemError(
                "idempotency-key-reuse",
                detail="this Idempotency-Key was used to submit a different "
                       "job") from None
        job = self._row(job["id"])

        if stages:
            # 🔴 Fetched after submit, while `staging`: no request waits on a
            # slow git host, and nothing queues until every source is in hand.
            self._start_preparing(job["id"])
            return self.wire(job)

        self._dispatch(session, job, derived, entries)
        return self.wire(self._row(job["id"]))

    ######################################################################
    # What a run's files are, and where the server's copies come from
    ######################################################################

    def _account(self, session, job, derived, unpacked: Path):
        '''Every file the manifest names, as how it reaches the run; refuse
        what nobody can supply.

        🔴 **No path the job names is read** (D112) -- see `owners.account`.
        `resource-unavailable` is raised only for what the caller could not
        send either (D127): a private dataroot this server has no copy of, a
        private design, or a path that escapes the root it is supplied under.
        '''
        entries = owners.account(derived["project"], unpacked / "sc_collected_files",
                                 self._supply, derived["required"])
        for entry in entries:
            if entry.status != owners.UNAVAILABLE:
                continue
            raise self._refuse(session, job, ProblemError(
                "resource-unavailable", resource_kind=entry.kind,
                resource=entry.name or "",
                detail=f"this flow needs a {entry.kind} this server cannot "
                       f"supply: {entry.why}"))
        for entry in entries:
            if entry.status == owners.UPLOADED:
                continue
            if entry.status == owners.SUPPLIED and entry.root:
                logger.info(f"{job['id']} is supplied {entry.kind} {entry.name} "
                            f"({entry.dataroot}) from this server")
        return entries

    def _check_environments(self, session, job, derived, unpacked: Path) -> None:
        '''A node's environment files, at submit (surface D131).

        Its presence is the declaration, so a job carrying one relies on
        `python.env` whether or not it said so at create -- and this deployment
        advertises it only where it can build one. Then every file is held to
        its path and its format, and every index it names to the index
        allowlist. A follow-up carrying one never gets here: it is
        `unrequested_member`, since only what was asked for may arrive.
        '''
        from siliconcompiler.remote import environment
        from siliconcompiler.remote.server import allowlist

        top = unpacked / environment.ROOT
        if not top.exists():
            return

        if "python.env" not in (self._config["features"] or ()):
            raise self._refuse(session, job, ProblemError(
                "feature-unsupported", feature="python.env",
                detail="this job carries a Python environment for a node, and this "
                       "deployment does not build one"))

        def refuse(detail):
            return self._refuse(session, job, ProblemError(
                "archive-rejected", violation="environment_file", detail=detail))

        nodes = set(derived["nodes"])
        rules = [allowlist.parse(entry) for entry in self._config["index_allowlist"] or []]
        declared, forwarded = set(), []
        for path in sorted(top.rglob("*")):
            if path.is_dir():
                continue
            name = path.relative_to(unpacked).as_posix()
            parts = name.split("/")
            node = tuple(parts[1:3])
            is_file = len(parts) == 4 and parts[3] == environment.FILENAME and node in nodes
            if not is_file and len(parts) >= 3 and parts[1] == environment.PACKAGES:
                # The job's own code, forwarded once beside the files: put on the
                # tool's PYTHONPATH, never installed, so nothing here parses it.
                forwarded.append(name)
                continue
            if not is_file:
                raise refuse(f"{name} is neither {environment.path_for('<step>', '<index>')} "
                             f"for a node of this flow nor under "
                             f"{environment.packages_path()}/")
            declared.add(node)
            try:
                parsed = environment.parse(path.read_bytes())
            except environment.EnvironmentFileError as e:
                raise refuse(f"{name}: {e}") from None
            for url in parsed.indexes:
                if not allowlist.allows(rules, url):
                    raise self._refuse(session, job, ProblemError(
                        "software-unavailable", reason="index-not-allowed", unresolved=[],
                        detail=f"{name} names the index {url}, which this server does "
                               "not let a build reach"))

        # The file is the declaration: forwarded packages with no node that has
        # one are not an environment anyone asked for.
        if forwarded and not declared:
            raise refuse(f"{forwarded[0]} is under {environment.packages_path()}/, and "
                         f"no node of this job has a {environment.FILENAME} to put it on "
                         "the path of")

    def _check_owed(self, session, job, derived, asked) -> None:
        '''Refuse a required value the client should have sent and did not.

        🔴 **Before anything dispatches (D129)**, rather than a node failing
        on a missing file. *Should have sent* is the design, anything local or
        editable, and anything this job already asked for; the rest the server
        can still ask for. Only a flow whose set is known is checked: without it
        there is no telling a missing file from one nothing reads.
        '''
        if derived["required"] is None:
            return
        before = {(item["kind"], item["name"], item["dataroot"])
                  for item in json.loads(job["upload_sources"] or "[]")}
        for entry in asked:
            if not (entry.kind == owners.DESIGN
                    or entry.origin in (owners.LOCAL, owners.EDITABLE)
                    or (entry.kind, entry.name, entry.dataroot) in before):
                continue
            where = f" ({entry.dataroot})" if entry.dataroot else ""
            raise self._refuse(session, job, ProblemError(
                "archive-rejected", violation="missing_member",
                detail=f"the flow reads [{','.join(entry.key or ())}] of {entry.kind} "
                       f"{entry.name}{where}, {entry.path}, and the archive does "
                       "not carry it"))

    def _requested_members(self, job, root: Path):
        '''What a follow-up archive may hold: the collected files of the
        dataroots this job asked for that the flow reads, and nothing else --
        a dataroot asked for selects its required values, never all of it.'''
        asked = {(item["kind"], item["name"], item["dataroot"])
                 for item in json.loads(job["upload_sources"] or "[]")}
        derived = self._derive(None, job, root)
        names = set()
        for one in owners._values(derived["project"]):
            if (one.kind, one.name, one.dataroot) in asked \
                    and owners.needed(one.key, derived["required"]):
                names.add(one.value.get_hashed_filename())

        def allowed(member: str) -> bool:
            parts = member.split("/")
            if parts == ["sc_collected_files"]:
                return True
            return len(parts) >= 2 and parts[0] == "sc_collected_files" \
                and parts[1] in names
        return allowed

    def _start_preparing(self, job_id: str) -> None:
        import threading

        with self._preparing_lock:
            if job_id in self._preparing:
                return
            self._preparing.add(job_id)
        threading.Thread(target=self._prepare, args=(job_id,), daemon=True,
                         name=f"prepare-{job_id[:8]}").start()

    @_as_data
    def _prepare(self, job_id: str) -> None:
        '''Fetch what the run needs and the server does not hold, then
        dispatch -- or send the job back asking for what could not be had.

        In parallel, a timeout per source and one deadline for the job. A
        transient failure is retried until the deadline; a permanent one --
        and whatever is still missing at the deadline -- goes back to the
        client, which has the credentials the server does not.
        '''
        import time
        from concurrent.futures import ThreadPoolExecutor

        from siliconcompiler.remote.server.sources import Permanent, Transient

        try:
            job = self._row(job_id)
            if job is None or job["state"] != "staging":
                return
            root = self.job_root(job["user_id"], job_id)
            unpacked = root / job["design"] / job["jobname"]
            derived = self._derive(None, job, root)
            entries = self._account(None, job, derived, unpacked)

            wanted = {}
            for entry in entries:
                if entry.status == owners.FETCH:
                    wanted.setdefault((entry.source, entry.ref), []).append(entry)

            timeout = self._config["fetch_timeout_seconds"]
            deadline = time.monotonic() + self._config["fetch_deadline_seconds"]
            # What only the client can send goes back with whatever fails to
            # fetch: one trip to `awaiting_input`, asking for all of it.
            failed = [(entry, "this server does not hold it and cannot fetch it")
                      for entry in entries if entry.status == owners.ASK]
            pause = 2
            while wanted:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    tried = {key: pool.submit(self._fetch, key[0], key[1], timeout)
                             for key in wanted}
                last = {}
                for key, future in tried.items():
                    try:
                        future.result()
                        wanted.pop(key)
                    except Permanent as e:
                        logger.info(f"{job_id}: a source cannot be fetched: {e}")
                        failed.extend((entry, str(e)) for entry in wanted.pop(key))
                    except Transient as e:
                        logger.info(f"{job_id}: a source did not answer, retrying: {e}")
                        last[key] = str(e)
                if wanted and time.monotonic() + pause >= deadline:
                    for key, entries_of in wanted.items():
                        why = f"no answer before the deadline ({last.get(key, 'timed out')})"
                        failed.extend((entry, why) for entry in entries_of)
                    wanted = {}
                elif wanted:
                    time.sleep(pause)
                    pause = min(pause * 2, 60)

            job = self._row(job_id)
            if job["state"] != "staging":
                # Cancelled while it waited.
                return

            if failed:
                self._send_back(job, failed)
                return

            # Everything in hand: a missing file in a fetched copy is refused
            # here, from `staging` -- and then it queues, and only moves on.
            entries = self._account(None, job, derived, unpacked)

            # Then each node's Python, built into an image on the one it
            # resolved to -- which needs the images resolved first.
            plan = self._build_environments(
                job, derived, self._resolve_images(None, job, derived))
            if self._row(job_id)["state"] != "staging":
                return

            with self._store.transaction():
                self._transition(job_id, "staging", "queued")
            self._dispatch(None, self._row(job_id), derived, entries, plan=plan)
        except ProblemError:
            # Already recorded on the job by `_refuse`.
            pass
        except _NoLongerStaging:
            # Cancelled while it waited: nothing to record.
            pass
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not prepare {job_id}: {e}")
            job = self._row(job_id)
            if job is not None and job["state"] in ("staging", "queued") \
                    and not job["scheduler_job_id"]:
                self._refuse(None, job, ProblemError(
                    "not-ready", status=503,
                    detail="this server could not prepare the job's sources"))
        finally:
            with self._preparing_lock:
                self._preparing.discard(job_id)
            self._store.release()

    def _fetch(self, source: str, ref: str, timeout: int) -> str:
        '''One source into this server's copy -- or, where `fetch_fails` is
        set, a permanent failure, so the job goes back to its client.'''
        from siliconcompiler.remote.server.sources import Permanent

        if self._config["fetch_fails"]:
            raise Permanent("this server fetches nothing (fetch_fails is set, as in "
                            "test mode 4)")
        return self._sources.fetch(source, ref, timeout)

    def _send_back(self, job, failed) -> None:
        '''`staging` back to `awaiting_input` -- the one backwards edge
        (surface D130) -- naming what failed, and nothing else.

        ``failed`` is ``(entry, why)`` pairs, and the transition says why for
        each: a job going backwards is the one move a person watching it will
        not expect, and "a source could not be fetched" tells them nothing
        about which or what to do.

        ⚠️ The job counts against `pending_uploads` again and frees its
        `concurrent_jobs` slot, both because those count by state; and
        `abandon_after_seconds` runs again from this transition.
        '''
        asked, reasons = [], []
        for entry, why in failed:
            if entry.wire not in asked:
                asked.append(entry.wire)
                reasons.append(f"{entry.kind} {entry.name} ({entry.dataroot}): {why}")
        reason = (f"{len(asked)} source(s) could not be fetched, so the client "
                  "is asked to send them -- " + "; ".join(reasons))
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_sources = ?, submit_idempotency_key = NULL "
                "WHERE id = ?", (json.dumps(asked), job["id"]))
            self._transition(job["id"], "staging", "awaiting_input",
                             reason=_bounded(reason))

    def _dispatch(self, session, job, derived, entries, plan=None) -> None:
        '''Resolve images, write the manifest the run will load, and hand
        the job to the scheduler. ``plan`` is the images already resolved
        while staging, with any a node's environment was built into.'''
        root = self.job_root(job["user_id"], job["id"])
        if plan is None:
            plan = self._resolve_images(session, job, derived)
        manifest = self._normalize(session, job, root, derived, plan, entries)

        try:
            bundle = self._framework_bundle(plan)
        except ProblemError as problem:
            raise self._refuse(session, job, problem) from None

        try:
            # The job's own root, so the batch script and the run's stdout land
            # beside what the run produced and go away with it when the job is
            # deleted.
            scheduler_job_id = self._dispatcher.submit(
                job["id"], root, manifest, image=bundle,
                queue=self._config["batch_queue"])
        except DispatchError as e:
            raise self._refuse(session, job, ProblemError(
                "not-ready",
                detail=f"this server could not hand the job to its "
                       f"scheduler: {e}")) from None

        self._record_submission(job, derived, scheduler_job_id, plan)
        logger.info(f"submitted {job['id']} as {scheduler_job_id}")

    ######################################################################
    # A node's Python environment, built into an image (surface D131)
    ######################################################################

    def _environments(self, job, derived) -> Dict[Tuple[str, str], str]:
        '''The file this server writes for each node whose environment it
        builds: none, unless nodes run in containers and the builder is on.

        🔴 **Written from what parsed, never the uploaded file** -- the same
        rendering host mode installs from. The file was held to the format at
        submit; this is the only form of it that goes further.
        '''
        from siliconcompiler.remote import environment

        if not (self._config["containers"] and self._config["env_builder"]):
            return {}

        unpacked = self.job_root(job["user_id"], job["id"]) / job["design"] / job["jobname"]
        found = {}
        for node in derived["nodes"]:
            path = unpacked / environment.path_for(*node)
            if not path.is_file():
                continue
            parsed = environment.parse(path.read_bytes())
            if parsed.pins:
                found[node] = environment.render(
                    parsed.pins, parsed.index_url, parsed.extra_index_urls,
                    header="Written by sc-server from what the job's file declared; "
                           "the file itself is never installed.")
        return found

    def _build_environments(self, job, derived, plan):
        '''``plan`` with every node that has an environment moved onto the
        image built for it -- reused where one exists for its base and file,
        built otherwise. Nodes whose files are identical share one build.

        🔴 **An environment that will not install rejects the job** from
        `staging`: `software-unavailable`, `reason: "uninstallable"`, naming
        each package and the target Python and platform. Never asked for as an
        upload -- the package could carry binaries this server cannot run.
        '''
        wanted = self._environments(job, derived)
        if not wanted:
            return plan

        nodes, refs = dict(plan.nodes), dict(plan.refs)
        done: Dict[str, Tuple[str, str]] = {}
        for node, text in sorted(wanted.items()):
            base_id = nodes.get(node)
            base_ref = refs.get(base_id) if base_id else None
            if not base_ref:
                raise self._refuse_staging(job, ProblemError(
                    "not-ready", status=503,
                    detail=f"{node[0]}/{node[1]} has no image to build its Python "
                           "environment on"))
            key = images.derivation(base_ref.split("@", 1)[1], text, _python_names(job))
            if key not in done:
                done[key] = self._derived_for(job, node, base_id, base_ref, key, text)
            image_id, ref = done[key]
            nodes[node] = image_id
            refs[image_id] = ref
        return images.Plan(plan.job, nodes, refs)

    def _derived_for(self, job, node, base_id, base_ref, key, text) -> Tuple[str, str]:
        '''The derived image for one base and file, as (id, pinned ref).'''
        import threading

        def found():
            row = images.derived_image(self._store, base_id, key)
            return (row["id"], images.pinned_ref(row["registry_ref"], row["digest"])) \
                if row else None

        existing = found()
        if existing:
            return existing

        with self._building_lock:
            lock = self._building.setdefault(key, threading.Lock())
        with lock:
            existing = found()
            if existing:
                return existing
            result = self._run_build(job, node, base_ref, key, text)
            image_id = images.register_derived(
                self._store, base_id, result["ref"], result["digest"], key,
                [tuple(pair) for pair in result.get("installed") or []],
                note=f"{node[0]}/{node[1]}'s Python environment, first built for "
                     f"job {job['id']}, on {result.get('python')} "
                     f"({result.get('platform')})")
            logger.info(f"{job['id']}: built {node[0]}/{node[1]}'s environment as "
                        f"{result['ref']}")
            return image_id, images.pinned_ref(result["ref"], result["digest"])

    def _refuse_staging(self, job, problem: ProblemError) -> ProblemError:
        '''`_refuse`, for a job that may have moved on while it waited.

        🔴 A build can take minutes, and a job cancelled meanwhile is
        `cancelled`: refusing it afterwards would rewrite what its owner did as
        something the server decided.
        '''
        current = self._row(job["id"])
        if current is None or current["state"] != "staging":
            raise _NoLongerStaging(job["id"])
        return self._refuse(None, current, problem)

    def _run_build(self, job, node, base_ref, key, text) -> Dict[str, Any]:
        '''One build, as a job of its own in the builder queue; its result, or
        the job refused with why.'''
        import uuid

        from siliconcompiler.remote.server import envbuild

        workspace = self._datadir / "envbuilds" / f"{key[:16]}-{uuid.uuid4().hex[:8]}"
        workspace.mkdir(parents=True)
        try:
            (workspace / envbuild.REQUIREMENTS).write_text(text)
            timeout = int(self._config["env_build_timeout_seconds"])
            (workspace / envbuild.SPEC).write_text(json.dumps({
                "key": key, "base_ref": base_ref, "base_digest": base_ref.split("@", 1)[1],
                "bundles_root": str(self.bundles_root()), "mounts": self.container_mounts(),
                "index_allowlist": list(self._config["index_allowlist"] or []),
                "timeout": timeout,
                "constrain": _python_names(job),
                "comment": f"sc-server: a node's Python environment ({key[:12]})",
            }, indent=1))

            try:
                build_id = self._dispatcher.submit_build(
                    key[:12], workspace, workspace / envbuild.SPEC,
                    queue=self._config["build_queue"])
            except DispatchError as e:
                raise self._refuse_staging(job, ProblemError(
                    "not-ready", status=503,
                    detail=f"this server could not start the build of "
                           f"{node[0]}/{node[1]}'s Python environment: {e}")) from None
            logger.info(f"{job['id']}: building {node[0]}/{node[1]}'s environment "
                        f"as {build_id}")

            result = envbuild.wait_for(
                workspace, timeout, alive=lambda: self._dispatcher.is_alive(build_id),
                **self._build_wait)
            if result is None:
                self._dispatcher.cancel(build_id)
                log = workspace / envbuild.LOG
                tail = "\n".join(log.read_text(errors="replace").strip().splitlines()[-10:]) \
                    if log.is_file() else ""
                raise self._refuse_staging(job, ProblemError(
                    "not-ready", status=503,
                    detail=_bounded(f"the build of {node[0]}/{node[1]}'s Python environment "
                                    f"did not finish within {timeout}s" +
                                    (f":\n{tail}" if tail else ""))))
            if not result.get("ok"):
                raise self._refuse_staging(job, _build_refusal(node, text, result))
            return result
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _check_denied(self, session, job, derived) -> None:
        '''Refuse a run that uses a PDK, library or tool nobody may use.

        🔴 **After re-derivation and before image resolution**: what the
        manifest names is only known once it is open, and *you may not use it*
        is asked before *can this server provide it* -- a denied tool this
        deployment has no image for is still a denial, and the caller should
        hear the answer that does not change when an image is added.

        ⚠️ The first one found is the one named, in the order PDK, library,
        tool, because the slug carries one `resource`. The detail says how many
        more there are, so fixing one is not followed by a surprise.
        '''
        wanted = _resources(derived) + [("tool", name) for name in derived["tools"]]

        denied = [(kind, name) for kind, name in wanted
                  if self._config.denied(kind, name)]
        if not denied:
            return

        kind, name = denied[0]
        more = len(denied) - 1
        raise self._refuse(session, job, ProblemError(
            "entitlement-denied", resource_kind=kind, resource=name,
            detail=f"this flow uses a {kind} this deployment does not allow"
                   + (f", and {more} more" if more else "")))

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

        requires = requirements(json.loads(job["descriptor"]) or {})

        flow = derived["project"].get_flow()
        inherits = runspec.inheriting_nodes(flow, derived["nodes"],
                                            derived["edges"])

        try:
            return images.plan_for_job(self._store, requires,
                                       derived["node_tools"], inherits)
        except ProblemError as problem:
            # Its own slug, not a guessed one: `plan_for_job` refuses for more
            # than one reason and the job must record the one the caller was
            # given.
            raise self._refuse(session, job, problem) from None

    def _framework_bundle(self, plan) -> Optional[str]:
        '''The container the job's own orchestrating process runs in.

        🔴 This is what makes version matching real rather than half-done. The
        per-node images decide what each TOOL runs in; this decides what
        interprets the manifest -- and without it a job asking for
        SiliconCompiler 0.39 has its flow driven by whatever version the cluster
        installed, which is the question version-matched-images.md calls the
        real one.

        Staged here rather than on the compute node, because `sbatch
        --container` names a bundle that has to exist before the job starts and
        there is nothing running yet to unpack it. It is a no-op once staged, so
        the cost falls on the first submit after an operator registers an image
        -- and `registry add-image -stage` is how an operator keeps it off the
        request path entirely.
        '''
        if self._dispatcher.name != "slurm" or not plan.job:
            return None

        ref = plan.refs.get(plan.job)
        if not ref:
            return None

        try:
            return str(images.stage_bundle(self.bundles_root(), ref,
                                           ref.split("@", 1)[1],
                                           mounts=self.container_mounts()))
        except Exception as e:                                   # noqa: BLE001
            # Refused rather than dispatched without it. Dropping the image
            # silently would run the job against whatever SiliconCompiler this
            # cluster has, which is the thing the registry exists to stop --
            # and it would do it while the record said otherwise.
            # The server's own failure, not the caller's request: `not-ready`,
            # as a scheduler refusing the handoff is.
            raise ProblemError(
                "not-ready", status=503,
                detail=f"this server could not unpack the image its own job "
                       f"needs to run in: {e}") from None

    def _record_submission(self, job, derived, scheduler_job_id, plan) -> None:
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET manifest_flow = ?, manifest_nodes = ?, "
                "  manifest_tools = ?, manifest_pdk = ?, "
                "  scheduler_job_id = ?, image_id = ?, submitted_at = ? "
                "WHERE id = ?",
                (derived["flow"], len(derived["nodes"]),
                 json.dumps(derived["tools"]), derived["pdk"],
                 scheduler_job_id, plan.job, now(), job["id"]))

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

    def _check_concurrent_jobs(self, user_id: str) -> None:
        active = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            "AND state IN ('staging', 'queued', 'running', 'cancelling')", (user_id,))["n"]
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
            raise self._refuse(session, job, ProblemError(
                "declared-mismatch",
                detail=f"the archive holds no {job['design']}/{job['jobname']}/"
                       f"{job['design']}.pkg.json"))

        # 🔴 Reading a manifest is only BACKWARDS compatible, and the failure
        # in the other direction is silent. SiliconCompiler migrates an older
        # manifest, but a newer one holds keys this schema does not have: they
        # are dropped, and a value whose type or legal values changed since is
        # rejected or replaced by its default. So the read "either fails or
        # quietly returns something other than what was written" -- and this
        # server acts on what it read, deciding the node list, the flow and the
        # limits from it.
        #
        # Caught rather than re-derived, because SiliconCompiler already knows
        # when it is out of its depth and says so; what is wrong is only that
        # it says it as a warning, which is right for a scheduler that can rerun
        # the node and wrong for a server admitting somebody else's work.
        with warnings.catch_warnings(record=True) as raised:
            warnings.simplefilter("always", SchemaVersionWarning)
            try:
                # Whole, not lazily: every class it names is resolved here,
                # inside `_as_data`, and none is left to a later access.
                project = Project.from_manifest(filepath=str(manifest), lazyload=False)
            except Exception as e:
                raise self._refuse(session, job, ProblemError(
                    "declared-mismatch",
                    detail=f"the uploaded manifest could not be read: {e}")) from None

        newer = [str(warning.message) for warning in raised
                 if issubclass(warning.category, SchemaVersionWarning)]
        if newer:
            raise self._refuse(session, job, ProblemError(
                "version-skew",
                detail=f"this server cannot read that manifest: {newer[0]}. "
                       "It was written by a newer SiliconCompiler than this "
                       "deployment runs, and reading one is only backwards "
                       "compatible"))

        if project.name != job["design"] or project.option.get_jobname() != job["jobname"]:
            raise self._refuse(session, job, ProblemError(
                "declared-mismatch",
                detail=f"the manifest is {project.name}/{project.option.get_jobname()} "
                       f"and the job is {job['design']}/{job['jobname']}"))

        try:
            runtime = runspec.runtime_flow(project)
            nodes = list(runtime.get_nodes())
        except Exception as e:
            raise self._refuse(session, job, ProblemError(
                "declared-mismatch",
                detail=f"the manifest names no runnable flow: {e}")) from None

        if not nodes:
            raise self._refuse(session, job, ProblemError(
                "declared-mismatch",
                detail="the manifest's flow has no nodes to run"))

        if len(nodes) > self._config.limits["max_job_nodes"]:
            raise self._refuse(session, job, ProblemError(
                "node-limit-exceeded", limit="max_job_nodes",
                detail=f"{len(nodes)} nodes, and this server runs at most "
                       f"{self._config.limits['max_job_nodes']}"))

        # 🔴 A node's task class this installation does not provide is refused
        # (surface D163): its own setup and pre- and post-processing run on the
        # node, so running it as its base class would silently lose them. Only
        # task classes -- a Design, flow or library subclass is data this
        # server never calls, and SiliconCompiler's own examples define theirs
        # in the script. Looked up, never imported: see `_as_data`.
        self._check_task_classes(session, job, project, nodes)
        self._check_unattended(session, job, project, nodes)

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

        node_tools = runspec.node_tools(project.get_flow(), nodes)

        return {
            "project": project,
            "flow": project.get_flow().name,
            "nodes": nodes,
            "edges": edges,
            "node_tools": node_tools,
            "tools": sorted({tool for tool in node_tools.values() if tool}),
            "pdk": _pdk(project),
            "libraries": _libraries(project),
            "fpga": _fpga(project),
            # What the flow reads (D129), from the `require` the client worked
            # out and carried here; None where it could not.
            "required": owners.required(project),
        }

    def _check_unattended(self, session, job, project, nodes) -> None:
        '''🔴 A job nobody is at (surface D165): a node that would wait for a
        person is refused rather than left to hang its allocation until the
        deadline. A breakpoint, or a task that opens a window -- every
        `ShowTask`, OpenROAD's `WebTask` -- but not a `ScreenshotTask`, which
        renders headless.'''
        from siliconcompiler import OpenTask, ScreenshotTask

        flow = project.get_flow()
        for step, index in nodes:
            if project.option.get_breakpoint(step=step, index=index):
                raise self._refuse(session, job, ProblemError(
                    "archive-rejected", violation="breakpoint",
                    detail=f"{step}/{index} has a breakpoint set, which stops the run "
                           "for a person to look -- and nobody is at a remote run. "
                           "Clear option,breakpoint for it"))
            try:
                task = flow.get_task_module(step, index)
            except ImportError:
                continue                    # `_check_task_classes` said so first
            if issubclass(task, OpenTask) and not issubclass(task, ScreenshotTask):
                raise self._refuse(session, job, ProblemError(
                    "archive-rejected", violation="interactive_task",
                    detail=f"{step}/{index} runs {task.__module__}/{task.__name__}, "
                           "which opens a window for a person -- and nobody is at a "
                           "remote run. A screenshot task renders the same view "
                           "without one"))

    def _check_task_classes(self, session, job, project, nodes) -> None:
        from siliconcompiler.schema.baseschema import BaseSchema

        known = BaseSchema._known_classes()
        if known is None:
            # Outside `_as_data`, where nothing is refused because nothing is
            # looked up -- which no caller that reads an upload is.
            return

        flow = project.get_flow()
        unknown: Dict[str, List[str]] = {}
        for step, index in nodes:
            name = flow.get_graph_node(step, index).get_taskmodule()
            if name not in known:
                unknown.setdefault(name, []).append(f"{step}/{index}")
        if not unknown:
            return

        named = "; ".join(f"{', '.join(where)} runs {name}"
                          for name, where in sorted(unknown.items()))
        raise self._refuse(session, job, ProblemError(
            "software-unavailable", reason="unknown_class",
            unresolved=[{"name": name, "requirement": [], "available": []}
                        for name in sorted(unknown)],
            detail=_bounded(f"this server does not have the task class each of these "
                            f"nodes runs: {named}. A task's own setup runs on the node, "
                            "so it is not run as its base class instead")))

    def _normalize(self, session, job, root: Path, derived, plan, entries=()) -> Path:
        '''Apply the server's settings and write the manifest the run will load.

        One place, once, after the digest check and after the archive limits
        bound. The list itself is in `runspec.normalize`, which is the file both
        ends read.
        '''
        project = derived["project"]

        cache = self.cache_dir(job["user_id"])
        cache.mkdir(parents=True, exist_ok=True)

        # Where each node's image reaches it depends on what is scheduling: a
        # Slurm step names an unpacked bundle, and the docker scheduler pulls a
        # digest. The dispatcher is the only thing that knows which.
        placements = plan.placements()
        sources = {}

        if self._dispatcher.name == "slurm":
            refs = placements
            placements = {}
            for node, ref in refs.items():
                bundle = str(images.bundle_path(self.bundles_root(),
                                                ref.split("@", 1)[1]))
                placements[node] = bundle
                sources[bundle] = ref

        runspec.normalize(project, job["id"], root, cache, images=placements,
                          cluster=self._dispatcher.name)

        # 🔴 Every dataroot points at the copy the run will actually read --
        # this job's upload, or this server's own supplied copy -- so the
        # manifest the run writes records which, and no dataroot is left
        # naming a path on the submitter's machine (D111, D112).
        runspec.point_dataroots(
            project, entries, root / job["design"] / job["jobname"] / "sc_collected_files")

        # Only the bundles need a source: a digest the docker scheduler pulls
        # already says where it comes from.
        runspec.write_images(
            root / job["design"] / job["jobname"] / runspec.IMAGES_FILENAME,
            sources, self.container_mounts() if sources else [],
            python=_python_names(job))

        manifest = root / job["design"] / job["jobname"] / f"{job['design']}.pkg.json"
        project.write_manifest(str(manifest))
        return manifest

    def _refuse(self, session, job, problem: ProblemError) -> ProblemError:
        '''Record a refusal, and hand back the problem for the caller to raise.

        A refused job is `rejected` and never `failed`: a refused job never ran,
        and keeping it out of `failed` is what stops a run of entitlement
        denials reading as a run of broken designs.

        🔴 **What is stored is the problem the caller was handed, whole.** The
        two used to be written separately and drifted: a job the scheduler
        would not take was recorded as `run-failed` while its submitter was
        told `not-ready`, so the person and the page they were looking at
        disagreed about a job neither of them could re-read. Taking the
        `ProblemError` itself is what makes that impossible rather than
        unlikely.

        🔴 **And the stored reason is the problem's `detail`, not its slug.**
        The slug is already `jobs.error_type` and is published as `error.type`;
        writing it a second time as prose told a person nothing they could not
        already see, while `detail` -- *which* limit, *which* mismatch -- was
        computed one line later and thrown away.
        '''
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (problem.error.uri, now(), job["id"]))
            self._transition(job["id"], job["state"], "rejected",
                             actor=session.user_id if session else None,
                             reason=problem.detail or problem.error.slug)
        self._storage.discard_upload(job["id"])
        if problem.error.slug == "upload-forbidden":
            self._forget_upload(job)
        return problem

    def _forget_upload(self, job) -> None:
        '''🔴 Delete the upload `upload-forbidden` refused, on either detection
        -- restricted material is not kept (surface D133). The row goes too:
        what remains is the job, its reason and the transition, which name the
        member and its hash; the refusal's `detail` is where the raiser puts
        both.'''
        row = self._store.one(
            "SELECT id, storage_key FROM artifacts WHERE job_id = ? AND upload_seq = "
            "(SELECT max(upload_seq) FROM artifacts WHERE job_id = ?)",
            (job["id"], job["id"]))
        if row is None:
            return
        self._storage.artifact_path(row["storage_key"]).unlink(missing_ok=True)
        with self._store.transaction():
            self._store.execute("DELETE FROM artifacts WHERE id = ?", (row["id"],))
        logger.warning(f"{job['id']}: deleted an upload refused as upload-forbidden")

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
            self._dispatcher.cancel(job["scheduler_job_id"],
                                    node_job_ids=self._node_job_ids(job))

        # A running job goes to `cancelling` and the scheduler writes the
        # terminal state; one that never started has nothing to wind down, so it
        # goes straight to `cancelled`.
        target = ("cancelling"
                  if job["state"] in ("queued", "running") and job["scheduler_job_id"]
                  else "cancelled")

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

    def whodunnit(self, session) -> str:
        """Where an action came from, in words, for a reason nobody supplied.

        🔴 **Prose and never a published user id.** Somebody reading *who took
        my results* wants the machine, and an id is a lookup they cannot do --
        while publishing one tells every reader of the job which account acted.
        The device's own name is what a person recognises, because it is what
        they named it.

        ⚠️ A portal session carries no device, and says so rather than
        inventing one: the browser is the surface, not a machine.
        """
        if not getattr(session, "device_id", None):
            return "the portal"

        device = self._store.one("SELECT name FROM devices WHERE id = ?",
                                 (session.device_id,))
        where = (device["name"] if device else "").strip()
        return f"sc-remote on {where}" if where else "sc-remote"

    def _deleted_from(self, session) -> str:
        '''`delete_reason` for a job's delete, which carries no body (surface
        D150): *deleted through the API from <device>*, or *deleted from the
        portal*.'''
        if not getattr(session, "device_id", None):
            return "deleted from the portal"
        device = self._store.one("SELECT name FROM devices WHERE id = ?",
                                 (session.device_id,))
        label = (device["name"] if device else "").strip()
        return f"deleted through the API from {label}" if label else \
            "deleted through the API"

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
        for path in (self.stream_index_path(job["id"]),
                     Path(f"{self.stream_index_path(job['id'])}.lock")):
            path.unlink(missing_ok=True)
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
            "  delete_reason = ? WHERE job_id = ? AND deleted_at IS NULL",
            (now(), session.user_id, self._deleted_from(session), job["id"]))

    def discard_node(self, session, job_id: str, step: str, index: str,
                     reason: str) -> int:
        '''Throw away what ONE node produced, and keep the run.

        🔴 **The node is the unit of deletion, and per-artifact would be the
        wrong grain.** There is no deleting a node's reports and keeping its
        logs: the node archive holds both, so removing one row while the
        archive still carried a copy would free nothing and make its
        `deleted_at` a claim the disk disagreed with. Taking the coordinates
        together is what actually reclaims the space.

        ⚠️ Job-level rows -- the manifest, the run's own log -- belong to no
        node and are never touched here. `discard_artifacts` is the whole-job
        version and takes those too.
        '''
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            raise ProblemError(
                "not-found", detail="this job's data was already deleted")

        if self._store.one(
                'SELECT 1 FROM job_nodes WHERE job_id = ? AND step = ? '
                'AND "index" = ?', (job_id, step, index)) is None:
            raise ProblemError(
                "not-found", detail=f"no node {step}/{index} in this job")

        rows = self._store.all(
            'SELECT id, location_id, storage_key FROM artifacts WHERE job_id = ? '
            'AND step = ? AND "index" = ? AND deleted_at IS NULL '
            "AND legal_hold_at IS NULL", (job_id, step, index))

        self._unlink(rows)
        if rows:
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                '  delete_reason = ? WHERE job_id = ? AND step = ? AND "index" = ? '
                "  AND deleted_at IS NULL AND legal_hold_at IS NULL",
                (now(), session.user_id, reason, job_id, step, index))

        # 🔴 The node's working tree goes with them, for the same reason the
        # whole-job version takes the job's: it is what these were indexed
        # FROM, so leaving it reclaims the smaller copy and keeps the larger
        # one. Only this node's directory, so the rest of the run is untouched.
        work = (self.job_root(job["user_id"], job["id"]) / job["design"] /
                job["jobname"] / step / index)
        shutil.rmtree(work, ignore_errors=True)

        logger.info(f"discarded {len(rows)} artifact(s) of {job_id} {step}/{index}")
        return len(rows)

    def _unlink(self, rows) -> None:
        '''Drop the bytes of some artifact rows. The rows are the caller's; an
        object another live row still names is left where it is.'''
        going = [row["id"] for row in rows]
        for row in rows:
            if artifacts.referenced_elsewhere(self._store, row, going):
                continue
            try:
                path = self._storage.artifact_path(row["storage_key"])
                if path.is_file():
                    path.unlink()
            except OSError as e:
                logger.debug(f"could not unlink {row['storage_key']}: {e}")

    def discard_artifacts(self, session, job_id: str, reason: str) -> int:
        '''Throw away what a run produced, and keep the run.

        🔴 **Not `DELETE /v1/jobs/{id}`, and the difference is the whole point.**
        Deleting the JOB sets `jobs.deleted_at`, which by the contract takes it
        out of the collection entirely -- the job is gone from every listing and
        reachable only by id. That is far more than somebody means when they
        ask to reclaim the space a finished run is using.

        This deletes the OBJECTS: the bytes go, every row stays and stays
        listed, and the job keeps its states, its timings and its place in the
        list. *Where did my results go* remains answerable, which is the entire
        reason the artifact rows outlive their contents.

        ⚠️ A legal hold is skipped rather than refused. One held object should
        not stop a person clearing the other forty, and the table would reject
        the write anyway -- an artifact cannot be both held and deleted.
        '''
        job = self.owned(session, job_id)

        if job["deleted_at"]:
            raise ProblemError(
                "not-found", detail="this job's data was already deleted")

        rows = self._store.all(
            "SELECT id, location_id, storage_key FROM artifacts "
            "WHERE job_id = ? AND deleted_at IS NULL AND legal_hold_at IS NULL",
            (job_id,))

        self._unlink(rows)
        if rows:
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                "  delete_reason = ? WHERE job_id = ? AND deleted_at IS NULL "
                "  AND legal_hold_at IS NULL",
                (now(), session.user_id, reason, job_id))

        # 🔴 The build tree goes with them. It is what the artifacts were
        # indexed FROM, so leaving it would reclaim the smaller copy and keep
        # the larger one -- and the portal reads a node's log out of it, which
        # would then outlive the artifact that replaced it.
        shutil.rmtree(self.job_root(job["user_id"], job["id"]),
                      ignore_errors=True)

        logger.info(f"discarded {len(rows)} artifact(s) of {job_id}")
        return len(rows)

    def archive(self, session, job_id: str, archived: bool) -> None:
        '''Put a job away, or take it back out.

        ⚠️ **A view preference and not an operation on the run**, which is why
        the contract gives it no endpoint and names the portal as its writer.
        Nothing about the job changes: a direct read still answers, every
        subresource still works, and only the default collection stops
        including it.

        🔴 Terminal only, and the constraint is in the schema as well as here.
        A queued job holds a `concurrent_jobs` slot and a created one holds a
        live upload grant, so hiding a job that is still going makes *why can I
        not submit* unanswerable from any screen.
        '''
        job = self.owned(session, job_id)

        if archived and job["state"] not in TERMINAL_STATES:
            raise ProblemError(
                "job-state-conflict",
                detail="only a job that has stopped can be archived: hiding a "
                       "running one makes 'why can I not submit' unanswerable")

        if archived:
            self._store.execute(
                "UPDATE jobs SET archived_at = ?, archived_by = ? WHERE id = ?",
                (now(), session.user_id, job_id))
        else:
            self._store.execute(
                "UPDATE jobs SET archived_at = NULL, archived_by = NULL "
                "WHERE id = ?", (job_id,))

    ######################################################################
    # Reconciliation: what the run says it is doing
    ######################################################################

    def reconcile(self, job) -> None:
        '''Read the run's progress file and move the store to match.

        The run writes a file beside its manifest; nothing calls back. That is
        what lets the process running the flow and the process serving this API
        be on different machines with nothing between them but a filesystem.
        '''
        if self.abandon_if_expired(job):
            return

        root = self.job_root(job["user_id"], job["id"])
        progress = runspec.read_progress(
            root / job["design"] / job["jobname"] / runspec.PROGRESS_FILENAME, root)

        if progress is None:
            # Nothing written yet. Either it has not started, or it never will.
            if job["scheduler_job_id"] and not self._alive(job):
                self._lost(job)
            elif job["state"] == "staging":
                # Its sources are being fetched -- or were, by a process that
                # has since restarted. Picked up again; a fetch that finished is
                # held and costs nothing.
                self._start_preparing(job["id"])
            return

        for key, node in (progress.get("nodes") or {}).items():
            step, _, index = key.partition("/")
            state = node.get("state", "pending")

            # 🔴 A published field with no writer is a published field that
            # lies. `error_type` was null on every node this server has ever
            # run, including the ones that failed, so a client could not tell
            # *this node is why* from *this node is fine* without re-deriving
            # it from the state it already had. `run-failed` is registered
            # precisely for this: it is one of the three slugs that are never
            # an HTTP response and only ever a `type` on an error object.
            error_type = f"{TYPE_BASE}/run-failed" if state == "failed" else None

            self._store.execute(
                'UPDATE job_nodes SET state = ?, started_at = ?, finished_at = ?, '
                '  exit_code = ?, error_type = ? '
                'WHERE job_id = ? AND step = ? AND "index" = ?',
                (state, node.get("started_at"), node.get("finished_at"),
                 node.get("exit_code"), error_type, job["id"], step, index))

            if state in TERMINAL_NODE_STATES:
                # Indexed as the node finishes rather than as the job does, so
                # a node that is done answers /logs with its archive while the
                # rest of the flow is still running -- which is precisely the
                # moment somebody tailing it asks.
                self._index_node(job, step, index)

        self._record_node_jobs(job)

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
        elif reported == "running" and self._silent(progress):
            # 🔴 The run has stopped saying anything, and that is evidence the
            # scheduler cannot give. See `_silent`.
            logger.warning(f"{job['id']} has not reported since "
                           f"{progress.get('heartbeat')}")
            self._lost(job)
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
            job_root = self.job_root(job["user_id"], job["id"])
            settled = runspec.read_progress(
                job_root / job["design"] / job["jobname"] / runspec.PROGRESS_FILENAME,
                job_root)

            if settled and settled.get("state") in ("completed", "failed"):
                self._finish(job, settled["state"], settled)
            else:
                self._lost(job)

    def _silent(self, progress) -> bool:
        '''Whether a run that claims to be going has stopped saying so.

        🔴 **The backstop for a scheduler that is wrong, which is not
        hypothetical.** A dynamic node killed without deleting itself leaves
        Slurm reporting its jobs RUNNING for ever on a machine that is gone --
        observed, for thirteen minutes, on a container that no longer existed.
        Every other check here asks the scheduler, so every other check
        believed it.

        The runner writes a heartbeat on a timer rather than on node
        transitions, because a single OpenROAD node runs for half an hour
        without a transition: *nothing written lately* and *dead* had to be
        told apart, and only a clock can do it.

        ⚠️ **No heartbeat means no opinion.** A run started by a runner older
        than this writes none, and the honest answer for it is the one this
        server always gave -- ask the scheduler. Treating a missing field as
        silence would declare every in-flight job of an upgrade dead.
        '''
        beat = progress.get("heartbeat")
        if not beat:
            return False

        patience = self._config["run_heartbeat_seconds"]
        return beat < _ago(patience)

    def abandon_if_expired(self, job) -> bool:
        '''A job whose upload never arrived reaches a terminal state.

        🔴 **`abandoned` is the tenth state and this is the only thing that
        writes it.** Until now a job created and never uploaded to sat in
        `created` for ever: it held a `pending_uploads` slot, it appeared on
        every listing, and -- because the portal refreshes until a job is
        terminal -- its page reloaded itself indefinitely for a run that was
        never going to happen.

        ⚠️ **Two ways to expire, because there are two ways to stall.** A job
        that asked for a grant has one that lapses, which is the contract's
        case. A job that was created and never asked has no expiry at all, so
        the clock runs from its creation instead -- otherwise the only jobs
        that could ever be abandoned are the ones that got furthest.

        Returns whether it moved, so a caller can stop looking at it.
        '''
        if job["state"] not in ("created", "awaiting_input"):
            return False

        # The later of the two: old enough by the operator's clock, AND not
        # holding a grant that is still good. A job whose upload is legitimately
        # in flight has a live grant and is never taken.
        # ⚠️ From the latest transition, not from creation: a job sent back
        # to `awaiting_input` (D124) gets the clock again.
        deadline = max(
            _after(job["state_changed_at"] or job["created_at"],
                   self._config.limits["abandon_after_seconds"]),
            job["upload_grant_expires_at"] or "")
        if deadline > now():
            return False

        logger.info(f"{job['id']} was never uploaded to; abandoning it")
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?",
                (now(), job["id"]))
            self._transition(
                job["id"], job["state"], "abandoned",
                reason="the upload never arrived and the grant expired")

        self._storage.discard_upload(job["id"])
        return True

    def _reap_orphans(self, job) -> None:
        '''Stop the work a run left behind when it went away.

        🔴 Marking a node `cancelled` in the store does not cancel anything. A
        node is a scheduler job of its own, so a run that died abruptly leaves
        its nodes running with nobody watching -- and the record then says
        `cancelled` about work that is still burning a compute slot. Seen for
        real: an orchestrator that failed left an OpenROAD detailed route
        running for another fifty-five minutes.

        ⚠️ Only the jobs the scheduler still HAS. scancel answers an error for
        one that has finished, and a warning per finished node is how an
        operator learns to ignore warnings.
        '''
        nodes = [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ?', (job["id"],))]

        try:
            orphans = self._dispatcher.running_nodes(job["id"], nodes)
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"could not look for orphans of {job['id']}: {e}")
            return

        if not orphans:
            return

        logger.warning(f"{job['id']} left {len(orphans)} node job(s) behind; "
                       "cancelling them")
        self._dispatcher.cancel(None, node_job_ids=orphans)

    def node_placements(self, session, job_id: str):
        '''Per node: the image it ran in, and the scheduler job it became.

        Neither is published on the wire -- a registry path and a scheduler id
        are deployment detail -- so this is what the portal reads instead, and
        it goes through the same ownership predicate every other read does.

        ⚠️ It BACKFILLS. Accounting can lag the scheduler by seconds, so a node
        that finished just before its job did can be missing from every poll
        that ran and present by the time somebody looks. Asking at read time is
        what turns that from a permanent gap into a late answer, and it costs
        nothing once every node has an id.
        '''
        job = self.owned(session, job_id)
        self._record_node_jobs(job)

        refs = {row["id"]: row["registry_ref"]
                for row in self._store.all("SELECT id, registry_ref FROM images")}

        return {(row["step"], row["index"]):
                (refs.get(row["image_id"]), row["scheduler_job_id"])
                for row in self._store.all(
                    'SELECT step, "index", image_id, scheduler_job_id '
                    "FROM job_nodes WHERE job_id = ?", (job["id"],))}

    def _record_node_jobs(self, job, force: bool = False) -> None:
        '''Write down which scheduler job each node became.

        🔴 Two things need it and neither can be done without it. A cancel has
        to stop the work and not only the process coordinating it, now that a
        node is a job of its own; and *which Slurm job was that* is the question
        a person brings to a support thread, which nothing else can answer.

        🔴 **Throttled, because this is the only part of a poll that leaves the
        machine.** Every call is a `squeue`, and every `squeue` is one or more
        RPCs into slurmctld -- so at a one-second poll interval it would be one
        per second per running job, which is exactly the load
        `--max-connections` exists to throttle. `force` is for the two callers
        that cannot accept a stale answer: a cancel, which needs the ids to
        reach the work, and the last look before a job goes terminal.

        ⚠️ Asked for once and then never again. Only the nodes still missing an
        id are looked up, so a job whose nodes are all recorded costs nothing --
        which is what keeps this inside the once-per-run poll rather than
        turning it into per-node polling.
        '''
        missing = [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes '
            "WHERE job_id = ? AND scheduler_job_id IS NULL", (job["id"],))]

        if not missing:
            return
        if not force and not self._may_ask_scheduler(job["id"]):
            return

        try:
            found = self._dispatcher.node_jobs(job["id"], missing)
        except Exception as e:                                   # noqa: BLE001
            # A gap in the record, and nothing more: this runs inside a poll
            # that is answering somebody's request about the job itself.
            logger.debug(f"could not read node jobs for {job['id']}: {e}")
            return

        if not found:
            return

        with self._store.transaction():
            for (step, index), scheduler_id in found.items():
                self._store.execute(
                    "UPDATE job_nodes SET scheduler_job_id = ? "
                    'WHERE job_id = ? AND step = ? AND "index" = ?',
                    (scheduler_id, job["id"], step, index))

    def _node_job_ids(self, job):
        '''Every node job this run has, as far as the store knows.

        Refreshed first, because a node dispatched since the last poll has no
        id recorded and is exactly the one a cancel most needs to reach.
        '''
        self._record_node_jobs(job, force=True)

        return [row["scheduler_job_id"] for row in self._store.all(
            "SELECT scheduler_job_id FROM job_nodes "
            "WHERE job_id = ? AND scheduler_job_id IS NOT NULL", (job["id"],))]

    def _may_ask_scheduler(self, job_id: str) -> bool:
        """Whether enough time has passed to ask the scheduler again.

        ⚠️ In memory and per process, which is the right shape rather than a
        shortcut: it is a rate limit on THIS process's outbound calls, and two
        API processes each asking at their own floor is exactly what a floor
        per process means. Nothing depends on it being exact, and nothing is
        lost when it resets -- the worst case is one extra `squeue`.
        """
        import time as _time

        now_at = _time.monotonic()
        last = self._asked.get(job_id, 0.0)
        if now_at - last < SCHEDULER_QUERY_FLOOR:
            return False

        self._asked[job_id] = now_at
        return True

    def _alive(self, job) -> bool:
        try:
            return self._dispatcher.is_alive(job["scheduler_job_id"])
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not ask the scheduler about {job['id']}: {e}")
            # Cannot tell is not the same as gone, and declaring a live job lost
            # is the more expensive mistake.
            return True

    def _lost(self, job) -> None:
        '''The scheduler no longer has it and it never said how it ended.

        🔴 Unless somebody was cancelling it, in which case this IS how it
        ended. A cancel kills the run, so the very next poll finds a scheduler
        with no job and a progress file still saying `running` -- which is
        exactly the shape of a lost job and is not one. Telling a person their
        cluster ate the run they just stopped is worse than saying nothing.
        '''
        self._reap_orphans(job)

        if job["state"] == "cancelling":
            logger.info(f"{job['id']} is gone from the scheduler, as asked")
            self._settle_cancelled(job)
            return

        logger.warning(f"{job['id']} is gone from the scheduler with no result")
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET error_type = ?, finished_at = ? WHERE id = ?",
                (f"{TYPE_BASE}/scheduler-lost", now(), job["id"]))

            # 🔴 A node that had STARTED did not get cancelled, it died. The
            # contract glosses `cancelled` as *the job ended before this node
            # started*, so using it for a node that was running says something
            # false about the one node somebody will look at first -- it is
            # where the work stopped. `failed` is what *started and did not
            # finish* means.
            self._store.execute(
                "UPDATE job_nodes SET state = 'failed', error_type = ? "
                "WHERE job_id = ? AND state = 'running'",
                (f"{TYPE_BASE}/run-failed", job["id"]))

            # Everything the run never reached. These really did end before
            # they started.
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled' WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped')", (job["id"],))
            self._transition(
                job["id"], job["state"], "failed",
                reason="the scheduler no longer has this job and the run never "
                       "recorded how it ended")

    def _settle_cancelled(self, job) -> None:
        '''A cancel that has taken effect. No error: nothing went wrong.'''
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled' WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped')", (job["id"],))
            self._transition(job["id"], "cancelling", "cancelled", reason="cancelled")

    def _finish(self, job, state: str, progress) -> None:
        # Belt and braces, and cheap: a run that ended by crashing rather than
        # by finishing can leave the same orphans a lost one does, and on a
        # deployment where a node is not a scheduler job this asks nothing.
        if state == "failed":
            self._reap_orphans(job)

        # 🔴 One more look before nothing looks again. The LAST node to finish
        # is dispatched after the second-to-last poll and finishes before the
        # job does, so the poll that records the others has nothing to find for
        # it -- and once the job is terminal no poll runs at all. A diamond
        # flow came back with three of its four nodes carrying a scheduler id.
        self._record_node_jobs(job, force=True)

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
        """Index one node's log, reports and archive, as it finishes."""
        try:
            artifacts.collect_node(
                self._store, self._storage, self._config, job,
                self.job_root(job["user_id"], job["id"]), step, index)
        except Exception as e:                                   # noqa: BLE001
            logger.error(f"could not index {job['id']} {step}/{index}: {e}")

    ######################################################################
    # Artifacts
    ######################################################################

    def _surface_allows(self, surface: str, kind: str) -> bool:
        '''Whether ``surface`` hands over artifacts of ``kind``.

        🔴 **`api_fetchable_kinds` binds the API and not the portal**, for the
        reason `max_download_bytes` does: the portal is a person choosing one
        object. Both disagreements between the surfaces are decided from the
        one ``surface`` argument so that they are written down in one place.
        '''
        if surface not in SURFACES:
            raise ValueError(f"{surface} is not a surface")
        return surface == "portal" or self._config.api_fetchable(kind)

    def _members_refusal(self, row, surface: str) -> Optional[str]:
        '''Row 4: a `node` archive is fetchable only when every artifact at its
        coordinates is -- other `node` rows and `issue` excepted -- because it
        holds them all, and handing it over would hand over any one that is
        not. Returns the WORST member's refusal (D120), or None.'''
        if row["kind"] != "node":
            return None
        # `input` is not a member either: the node archive leaves `inputs/` out.
        members = self._store.all(
            'SELECT * FROM artifacts WHERE job_id = ? AND step = ? AND "index" = ? '
            "AND kind NOT IN ('node', 'issue', 'input')",
            (row["job_id"], row["step"], row["index"]))
        refusals = [artifacts.ladder(member, self._surface_allows(surface, member["kind"]))
                    for member in members]
        if "not-found" in refusals and not row["deleted_at"]:
            # 🔴 A member deleted on its own, under a live node archive
            # (entitlements D41). Handing the archive over would undo the
            # deletion, so it is `artifact-not-approved` -- and the state should
            # not exist, since a node is reaped with its first member, so an
            # operator is told: reaching it is a bug.
            if row["id"] not in _ALERTED:
                _ALERTED.add(row["id"])
                logger.error(f"node archive {row['id']} of job {row['job_id']} "
                             f"({row['step']}/{row['index']}) has a member deleted on "
                             "its own; a node is reaped as a whole, so this is a bug")
            refusals = ["artifact-not-approved" if refusal == "not-found" else refusal
                        for refusal in refusals]
        return artifacts.worst(refusals)

    def _refuse_by_ladder(self, row, surface: str) -> None:
        '''Raise the refusal the ladder's deciding row names, if any.'''
        refusal = artifacts.ladder(row, self._surface_allows(surface, row["kind"]),
                                   self._members_refusal(row, surface))
        if refusal is None:
            return
        if refusal == "not-found":
            raise ProblemError("not-found", detail="these bytes were deleted")
        if refusal == "not-ready":
            # Transient: it is still being described.
            raise ProblemError(
                "not-ready", artifact_kind=row["kind"],
                detail="this artifact is still being described",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})
        raise ProblemError(
            "artifact-not-approved",
            detail="this artifact is not handed over here; the web portal has it"
            if not self._surface_allows(surface, row["kind"])
            else "this artifact is held back from download")

    def artifacts(self, session, job_id: str, args, surface: str = "api"):
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

        items = [artifacts.wire(row, self._surface_allows(surface, row["kind"]),
                                self._members_refusal(row, surface))
                 for row in rows]
        return items, (_encode_cursor(rows[-1]) if more and rows else None)

    def artifact(self, session, job_id: str, artifact_id: str,
                 surface: str = "api"):
        '''Endpoint 22's row, with the refusals it can make.

        ``surface`` is what the two surfaces disagree about, and it is a
        parameter rather than two code paths so that the disagreement is
        written down in one place: ``"api"`` or ``"portal"``. 🔴
        **`max_download_bytes` and `api_fetchable_kinds` bind the API and not
        the portal.** There is no API override for it -- no query
        parameter, no header -- because a limit a caller can switch off is not
        a limit. The portal is the way past it, and it is allowed to be because
        it is a different surface with a person on it who has just clicked the
        object: a browser download is somebody deciding, one object at a time,
        and the ceiling exists to stop an automated sweep pulling gigabytes
        nobody asked for.
        '''
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

        self._refuse_by_ladder(row, surface)

        if surface == "api":
            self._check_download_ceiling(session, row)

        return row

    def _check_download_ceiling(self, session, row) -> None:
        '''Refuse one object that is larger than this caller may pull.

        🔴 The CALLER's number and not the deployment's: `max_download_bytes`
        is the one limit a `user_limits` row may override, so reading
        `config.limits` here would enforce a ceiling the account was
        deliberately lifted above. `None` is unlimited, which is the wire's
        meaning for it everywhere.

        🔴 `403 download-too-large` (D117), not `429 limit-exceeded`: that one
        means *refills*, and a client obeying its `Retry-After` on a ceiling
        that never refills would retry for ever. The download side of
        `upload-too-large`.
        '''
        from siliconcompiler.remote.server import accounts

        allowed = accounts.effective_limits(
            self._store, self._config, session.user_id)["max_download_bytes"]
        if allowed is None:
            return

        stored = row["size_bytes"] or 0
        if stored <= allowed:
            return

        raise ProblemError(
            "download-too-large", limit="max_download_bytes",
            detail=f"{units.size(stored)} is larger than the "
                   f"{units.size(allowed)} this account may download over the "
                   "API; open it from the web portal instead")

    def node_log(self, session, job_id: str, step: str, index: str,
                 surface: str = "api"):
        '''Endpoint 20's target: the archived log for one terminal node.

        Returns ``("stream", node)`` or ``("artifact", row)`` -- the two things
        a 303 can point at. Everything else this endpoint can answer is a
        refusal, and which one depends on the node's state rather than on the
        artifact: a node that has not run has no log, and saying `not-found`
        would tell a client to stop asking.

        ⚠️ ``features`` is what the API publishes, so it gates the API and not
        the portal -- which shows a node's log however the deployment answers
        a client. That is the same split ``surface`` makes for the artifacts.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        api = surface == "api"
        features = self._config["features"]
        if api and "logs" not in features and "logs.stream" not in features:
            # 🔴 Refused before the node is looked at, because it does not
            # depend on the node: this deployment serves no logs over the API,
            # so there is nothing to wait for and a client must not retry.
            raise ProblemError(
                "feature-unsupported", feature="logs",
                detail="this deployment does not serve logs over the API; "
                       "they are on the web portal")

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
            if api and "logs.stream" not in features:
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

        if api and "logs" not in features:
            # Only the live tail is served, and this node is over.
            raise ProblemError(
                "feature-unsupported", feature="logs",
                detail="this deployment serves a live log while a node runs "
                       "and does not keep one afterwards")

        # The same bytes as endpoint 22 and the same signed URL, so the same
        # refusals: a caller that cannot fetch a log as an artifact must not be
        # handed it by asking for it as a log.
        self._refuse_by_ladder(row, surface)
        if api:
            self._check_download_ceiling(session, row)

        return "artifact", row

    def job_log(self, session, job_id: str):
        '''Endpoint 20 with no coordinates: the whole job's live stream.

        Returns the job when the answer is a stream -- which it is for a job
        that is running AND for one that is over, whose stream sends `end` at
        once. Everything else is a refusal.

        🔴 **A missing capability is named at its broadest**: `logs`, then
        `logs.stream`, then `logs.stream.job`. A client told only that the job
        stream is missing, on a deployment that serves no logs at all, would
        fall back to per-node requests that fail too.

        ⚠️ The terminal answer is deliberately not a refusal. A job can end
        between the `303` and the connect, and the stream already answers that
        with `end`; a request that arrives after the end is the same case
        arriving late, and gets the same path.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        features = self._config["features"]
        for feature in ("logs", "logs.stream", "logs.stream.job"):
            if feature not in features:
                raise ProblemError(
                    "feature-unsupported", feature=feature,
                    detail=_WITHOUT[feature])

        if job["state"] in TERMINAL_STATES:
            return job

        started = self._store.one(
            "SELECT 1 FROM job_nodes WHERE job_id = ? "
            "AND state NOT IN ('pending', 'queued', 'preparing') LIMIT 1",
            (job["id"],))
        if started is None:
            # The same answer a node gives before it starts: transient.
            raise ProblemError(
                "not-ready", artifact_kind="logs",
                detail="no node of this job has started",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

        return job

    def job_nodes(self, job_id: str) -> List[Tuple[str, str]]:
        '''Every node of a job, in the one order a job stream's id relies on.'''
        return [(row["step"], row["index"]) for row in self._store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? '
            'ORDER BY step, "index"', (job_id,))]

    def node_states(self, job_id: str) -> Dict[Tuple[str, str], str]:
        '''What every node is doing NOW, read fresh for a stream that asks
        over and over.'''
        return {(row["step"], row["index"]): row["state"] for row in self._store.all(
            'SELECT step, "index", state FROM job_nodes WHERE job_id = ?', (job_id,))}

    def job_over(self, job_id: str) -> bool:
        row = self._store.one("SELECT state FROM jobs WHERE id = ?", (job_id,))
        return row is None or row["state"] in TERMINAL_STATES

    def node_logs(self, session, job_id: str, step: str, index: str):
        '''Every log one node left, as (name, path).

        🔴 A node writes more than one and they answer different questions.
        `sc_<step>_<index>.log` is SiliconCompiler's own record of the node --
        setup, inputs, timing -- and `<step>.log` is what the TOOL printed,
        which is where a synthesis error actually is. Offering only the first
        sends somebody looking for OpenROAD's complaint to a file that does not
        contain it.

        Read from the node's working directory rather than from the indexed
        artifact, because only one of them is indexed. Ownership was decided
        above, by the same predicate the API evaluates.
        '''
        job = self.owned(session, job_id)

        workdir = (self.job_root(job["user_id"], job["id"]) / job["design"] /
                   job["jobname"] / step / index)
        if not workdir.is_dir():
            return []

        # SiliconCompiler's own first: it is the one that says what the node
        # was asked to do, which is where to start when a node failed.
        own = f"sc_{step}_{index}.log"
        found = sorted(workdir.glob("*.log"),
                       key=lambda path: (path.name != own, path.name))
        return [(path.name, path) for path in found]

    def stream_index_path(self, job_id: str) -> Path:
        '''The job stream's event index (D121).

        Outside the job's build directory, which an uploaded archive fills: an
        index is the server's record of what it streamed, and a member could
        otherwise be one.
        '''
        return self._datadir / "streams" / f"{job_id}.idx"

    def read_node_file(self, session, job_id: str, path) -> str:
        '''A file out of one of this caller's job trees, as text -- a regular
        file under the job's root reached through no link. Raises OSError
        otherwise: a node's code can leave a link in its own tree, and reading
        through it would show the caller the host's files.'''
        job = self.owned(session, job_id)
        with confine.open_inside(self.job_root(job["user_id"], job["id"]), path,
                                 "r", errors="replace") as handle:
            return handle.read()

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

    def resolved_versions(self, job) -> Dict[str, List[str]]:
        """Every distribution version this job's images declare.

        The job image and each node's, taken together: a forty-node flow over
        six tools resolves six images, and *what did this run* is the union of
        what they hold.
        """
        rows = self._store.all(
            "SELECT DISTINCT image_id FROM job_nodes WHERE job_id = ? "
            "  AND image_id IS NOT NULL", (job["id"],))

        return images.contents_of(
            self._store, [job["image_id"], *(row["image_id"] for row in rows)])

    def web_url(self, job_id: str) -> Optional[str]:
        """This job's page for a person, where this deployment has one."""
        base = self._config["web_url_base"]
        return f"{base.rstrip('/')}/portal/jobs/{job_id}" if base else None

    def _why(self, job) -> Optional[str]:
        '''What actually went wrong, in the run's own words.

        🔴 Read back off `job_state_transitions` rather than stored a second
        time on the job. The transition into the state the job is in IS the
        record of why it got there -- `jobs` has an `error_type` and no
        `error_detail`, and adding one would mean two writers for one fact.

        The runner writes it into the progress file as the exception that
        ended the run, and the reaper and the refusal path write theirs the
        same way, so every terminal state has one and it is the same string
        the portal has always rendered in the history table.
        '''
        if not job["error_type"]:
            return None

        row = self._store.one(
            "SELECT reason FROM job_state_transitions "
            "WHERE job_id = ? AND to_state = ? ORDER BY id DESC LIMIT 1",
            (job["id"], job["state"]))
        return row["reason"] if row else None

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
            "error": _error(job["error_type"], self._why(job)),
        }

        # 🔴 Followed, never constructed. The portal's route shape may change
        # without a version bump, so a client that builds this itself breaks
        # quietly -- which is why it is published at all rather than left as
        # something an id could be pasted into.
        #
        # Absent, never null, where the deployment serves no web UI.
        page = self.web_url(job["id"])
        if page:
            body["web_url"] = page

        # 🔴 What it actually ran in. Once a request can carry a range, nothing
        # else answers *what did this job run* -- the descriptor says what was
        # asked for and this says what the server chose.
        #
        # ⚠️ Absent rather than empty where nothing was resolved: on a
        # deployment that runs jobs on the host there is no image and no
        # answer, and `{}` would claim this job ran nothing at all.
        resolved = self.resolved_versions(job)
        if resolved:
            body["resolved_versions"] = resolved

        # 🔴 Present only while the server is asking -- in `created` or
        # `awaiting_input` -- and never `[]` (D127): what to send, and nothing
        # else.
        if job["state"] in ("created", "awaiting_input") and job["upload_sources"]:
            asking = json.loads(job["upload_sources"])
            if asking:
                body["upload_sources"] = asking

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


# Node archives already reported as sitting over a member deleted on its own,
# so a client polling the listing does not raise the same alert every second.
_ALERTED: Set[str] = set()


class _Supply:
    '''What this server can supply by IDENTITY, never by a path a job names.'''

    def __init__(self, config, sources):
        self._config = config
        self._sources = sources

    def package(self, module: str) -> bool:
        '''Whether this installation has ``module``, asked without importing
        anything a job named (contract §1).

        ⚠️ `find_spec` on a dotted name imports its parent first, so only a
        top-level name is looked up -- which runs nothing -- and a submodule is
        answered only once its parent is already loaded here.
        '''
        import importlib.util
        import sys

        top, _, rest = module.partition(".")
        if not top.isidentifier() or (rest and top not in sys.modules):
            return False
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            return False

    def private_root(self, name, dataroot) -> Optional[str]:
        return ((self._config["private_dataroots"] or {}).get(name) or {}).get(dataroot)

    def held(self, source, ref) -> Optional[str]:
        # Nothing is held on a server that fetches nothing: a copy left from
        # before would supply the job and skip the path it exists to test.
        if self._config["fetch_fails"]:
            return None
        return self._sources.held(source, ref)

    def allowlisted(self, source, ref) -> bool:
        return self._sources.allowlisted(source, ref)


######################################################################
# Small things, kept out of the class
######################################################################

def requirements(descriptor: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """What a job needs from its image, in the two buckets: `descriptor.requires`.

    🔴 **The one member, and it names every Python distribution the job
    imports**, pinned exactly -- a name not in `requires` is not required, and
    the job may land in an image without it. `versions` is gone; so is the
    fallback to it (D126, superseded).

    🔴 **Each value is a LIST of PEP 440 specifier sets, any one of which
    satisfies**, and a bare string is refused: that is what SiliconCompiler
    means by a version requirement -- `Task.get('version')` is a list, and two
    tasks of one tool contribute two entries. `[]` is *any version*, which is
    not the same as leaving the name out.

    🔴 **Both buckets, and a flat map is refused.** The whole `python` set
    shares an interpreter and must be held by ONE image, while a tool is
    satisfied per node; accepting a flat map would mean guessing which.
    """
    from siliconcompiler.remote.server.images import BUCKETS

    buckets = tuple(BUCKETS.values())
    found: Dict[str, Dict[str, Any]] = {bucket: {} for bucket in buckets}

    given = descriptor.get("requires")
    if given is None:
        return found
    if not isinstance(given, dict):
        raise ProblemError("invalid-request", detail="requires must be an object")

    unknown = set(given) - set(buckets)
    if unknown:
        raise ProblemError(
            "invalid-request",
            detail=f"requires is keyed on {' and '.join(buckets)}; "
                   f"{', '.join(sorted(unknown))} is neither")

    for bucket in buckets:
        inner = given.get(bucket)
        if inner is None:
            continue
        if not isinstance(inner, dict):
            raise ProblemError(
                "invalid-request",
                detail=f"requires.{bucket} must be an object of name to requirement")
        for name, wanted in inner.items():
            if not isinstance(wanted, list) or not all(isinstance(one, str) for one in wanted):
                raise ProblemError(
                    "invalid-request",
                    detail=f"requires.{bucket}.{name} is a list of specifier sets, "
                           "even with one entry; a bare string is not")
        found[bucket] = dict(inner)

    return found


# 🔴 Strict on requests (contract.md): what each body may carry. `run_hash` is
# job reuse's, and top level: the descriptor is what submit re-derives.
CREATE_MEMBERS = ("design", "jobname", "project", "descriptor", "run_hash")
DESCRIPTOR_MEMBERS = ("flow", "needs", "requires", "sources")
SOURCE_MEMBERS = ("kind", "name", "dataroot", "source", "ref", "private")


def _only(body: Dict[str, Any], allowed, where: str) -> None:
    '''An unknown member is refused, never ignored: a misspelled optional
    member would otherwise be a check the caller believes they asked for.'''
    unknown = sorted(set(body) - set(allowed))
    if unknown:
        raise ProblemError(
            "invalid-request",
            detail=f"{where} has no member {unknown[0]!r}; it takes "
                   f"{', '.join(allowed)}")


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


_RUN_HASH = re.compile(r"^[\x20-\x7e]{1,128}$")


def _run_hash(value) -> Optional[str]:
    '''An opaque string of 1 to 128 printable ASCII characters, or absent.'''
    if value is None:
        return None
    if not isinstance(value, str) or not _RUN_HASH.match(value):
        raise ProblemError("invalid-request",
                           detail="run_hash is an opaque string of 1 to 128 printable "
                                  "ASCII characters")
    return value


def _opaque(value, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ProblemError("invalid-request",
                           detail=f"{field} is an opaque string of at most 200 characters")
    return value


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


def _resources(derived) -> List[Tuple[str, str]]:
    '''The PDK, libraries and FPGA device a derived flow needs, as
    ``(resource_kind, name)``, in the order a refusal names them.'''
    return (([("pdk", derived["pdk"])] if derived["pdk"] != "none" else []) +
            [("library", name) for name in derived["libraries"]] +
            ([("fpga", derived["fpga"])] if derived.get("fpga") else []))


def _fpga(project) -> Optional[str]:
    '''The FPGA device this run targets, or None for a flow with none.'''
    try:
        return project.get("fpga", "device") or None
    except Exception:                                           # noqa: BLE001
        return None


def _libraries(project) -> List[str]:
    '''The standard-cell libraries this run uses, main library first.

    ⚠️ `asic,asiclib` is filled in from the main library when a run starts, so
    a manifest that has never run can carry only `asic,mainlib`. Both are read.
    '''
    found: List[str] = []
    for key in ("mainlib", "asiclib"):
        try:
            value = project.get("asic", key)
        except Exception:                                       # noqa: BLE001
            continue
        for name in (value if isinstance(value, list) else [value]):
            if name and name not in found:
                found.append(name)
    return found


def _declared_sources(descriptor) -> Optional[List[Dict[str, Any]]]:
    '''The descriptor's `sources`, checked, with credentials stripped -- or
    None where there are none.

    `private` is OPTIONAL and defaults to false; 🔴 when true, `source` and
    `ref` are forbidden -- a private dataroot's path is never sent, and a
    client that sends one anyway is refused rather than trusted to be harmless.
    '''
    declared = descriptor.get("sources")
    if declared is None:
        return None
    if not isinstance(declared, list):
        raise ProblemError("invalid-request", detail="sources is a list")
    checked = []
    for item in declared:
        if not isinstance(item, dict) or item.get("kind") not in owners.SOURCE_KINDS \
                or not isinstance(item.get("name"), str) \
                or not isinstance(item.get("dataroot"), str) \
                or not isinstance(item.get("private", False), bool):
            raise ProblemError(
                "invalid-request",
                detail="each source is {kind, name, dataroot} with an optional source, "
                       f"ref and private, and kind is one of {', '.join(owners.SOURCE_KINDS)}")
        _only(item, SOURCE_MEMBERS, "a source")
        private = item.get("private", False)
        if private and ("source" in item or "ref" in item):
            raise ProblemError(
                "invalid-request",
                detail=f"{item['kind']} {item['name']} is private, so it carries no "
                       "source and no ref: its path never leaves the client")
        entry = {"kind": item["kind"], "name": item["name"],
                 "dataroot": item["dataroot"], "private": private}
        if isinstance(item.get("source"), str):
            # 🔴 Stripped again: a client that sent `user:token@` anyway has
            # its secret neither stored nor logged here.
            entry["source"] = owners.strip_userinfo(item["source"])
        if isinstance(item.get("ref"), str):
            entry["ref"] = item["ref"]
        checked.append(entry)
    return checked


def _python_names(job) -> List[str]:
    '''What the job's `requires.python` names: an environment is installed
    with each pinned to the version its image -- or host -- already holds.'''
    from siliconcompiler.remote.server.images import BUCKETS

    return sorted(requirements(json.loads(job["descriptor"] or "{}") or {})
                  [BUCKETS["python"]])


class _NoLongerStaging(Exception):
    '''The job left `staging` while it was being prepared.'''


def _build_refusal(node, text: str, result: Dict[str, Any]) -> ProblemError:
    '''What a failed environment build tells the job's owner.'''
    from siliconcompiler.remote import environment

    where = f"{node[0]}/{node[1]}"
    target = f"{result.get('python') or 'its Python'} ({result.get('version') or '?'}) " \
             f"on {result.get('platform') or 'its platform'}"
    if result.get("reason") != "uninstallable":
        return ProblemError(
            "not-ready", status=503,
            detail=_bounded(f"this server could not build {where}'s Python environment: "
                            f"{result.get('detail') or 'the build failed'}"))

    named = list(result.get("unresolved") or []) or \
        [str(pin) for pin in environment.parse(text.encode()).pins]
    unresolved = []
    for requirement in named:
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?(.*)$", requirement)
        name, spec = (match.group(1), match.group(3).strip()) if match else (requirement, "")
        unresolved.append({"name": re.sub(r"[-_.]+", "-", name).lower(),
                           "requirement": [spec] if spec else [], "available": []})

    refused = result.get("refused") or []
    tail = "\n".join((result.get("tail") or "").splitlines()[-5:])
    return ProblemError(
        "software-unavailable", reason="uninstallable", unresolved=unresolved,
        detail=_bounded(
            f"{where}'s Python environment will not install for {target}: "
            f"{', '.join(named)}"
            + (f"; the build was refused {', '.join(refused)}, which the index "
               "allowlist does not name" if refused else "")
            + (f"\n{tail}" if tail else "")))


def _bounded(text: str, limit: int = 1000) -> str:
    '''A transition reason, no longer than a page shows.'''
    return text if len(text) <= limit else text[:limit - 3] + "..."


def _after(when: str, seconds: int) -> str:
    """`seconds` after a stored timestamp, in the format the store writes.

    🔴 Milliseconds, three digits, exactly as `store.now()` writes them. These
    are compared as STRINGS against stored timestamps, so a fraction of the
    wrong length does not compare wrong by a rounding error -- it compares
    wrong by character: `.12Z` sorts after `.123Z`, because `Z` is above `3`.
    The first version of this truncated one digit too far and every deadline
    read as *not yet*.
    """
    from datetime import datetime, timedelta, timezone

    try:
        moment = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        # Unreadable is not a licence to abandon somebody's job.
        return "9999-12-31T23:59:59.999Z"

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment += timedelta(seconds=seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ago(seconds: int) -> str:
    """The timestamp `seconds` ago, in the one format this store writes.

    A string comparison, because that is what the column holds and what `now()`
    produces -- RFC 3339 in UTC to milliseconds sorts lexically.
    """
    from datetime import datetime, timedelta, timezone

    when = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return when.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _error(error_type: Optional[str],
           detail: Optional[str] = None) -> Optional[Dict[str, Any]]:
    '''A job's error, as an RFC 9457 object.

    🔴 `detail` is what makes it worth reading. `type` and `title` are frozen
    and identical on every deployment and for every occurrence -- *The run
    failed* is true of every failed run there has ever been -- so without a
    `detail` the object says only that something went wrong, which the `state`
    already said. The specific reason was being recorded on the transition and
    published nowhere, so a person on the CLI could not reach it at all.

    ⚠️ Bounded like every other `detail`, and this is the path that needs it
    most: a run's reason can be a tool's own exception text, which carries
    whatever paths the client's design named. It does not pass through
    `problem()`, so the bound is applied here rather than inherited.
    '''
    if not error_type:
        return None
    slug = error_type.rsplit("/", 1)[-1]
    title = ERRORS[slug].title if slug in ERRORS else "The job failed"

    body = {"type": error_type, "title": title}
    # Prose that only repeats the slug is not prose: the slug is already the
    # `type`, and a client branches on that.
    if detail and detail != slug:
        body["detail"] = bound(detail)
    return body


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
