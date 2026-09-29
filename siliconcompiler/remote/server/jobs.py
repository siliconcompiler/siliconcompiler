'''
The job: creating one, feeding it bytes, running it, and saying what it did.

Everything above this module is HTTP and everything below it is a filesystem or
a scheduler. The ordering rules that matter are here, and one of them is a
security property rather than a preference:

🔴 **submit checks the digest against what storage reports and answers `202`;
only then, while staging, is the archive extracted, the manifest read and every
check re-run against what the read returned.** Getting that order wrong is how
an archive bomb gets opened. Nothing in this file may be reordered without
reading that sentence again.

🔴 **No manifest is parsed in this process** (contract §1, *No server process
holding credentials parses a manifest*). The read runs while the job stages, in
a process of its own (`manifestread`, started by `sandbox`), and this module
acts only on the data summary it returns.
'''

import base64
import gzip
import hashlib
import json
import logging
import os
import re
import shutil

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from siliconcompiler.flowgraph import Flowgraph

from siliconcompiler.remote import owners, units
from siliconcompiler.remote.server import (
    archive, artifacts, confine, images, manifestread, runspec, sandbox)
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

# `sha256` is the only algorithm v1 accepts, and the prefix is always written.
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

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
    "logs.stream": "this deployment does not serve a live log; each node's "
                   "log is an artifact once it finishes",
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

# How long an `Idempotency-Key` is honoured (surface §6).
IDEMPOTENCY_SECONDS = 24 * 3600


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

        # Keyed requests being handled now, so a retry of one gets `in_progress`.
        self._in_flight: Set[Tuple[str, str, str]] = set()
        self._in_flight_lock = threading.Lock()

    def _keyed(self, user_id: str, what: str, key: Optional[str]):
        '''While a keyed request is handled; a retry meanwhile is refused
        `in_progress`, with `Retry-After`, and binds nothing.'''
        import contextlib

        if key is None:
            return contextlib.nullcontext()

        @contextlib.contextmanager
        def held():
            token = (user_id, what, key)
            with self._in_flight_lock:
                if token in self._in_flight:
                    raise ProblemError(
                        "job-state-conflict", reason="in_progress",
                        detail="a request with this Idempotency-Key is still being handled",
                        headers={"Retry-After": "1"})
                self._in_flight.add(token)
            try:
                yield
            finally:
                with self._in_flight_lock:
                    self._in_flight.discard(token)
        return held()

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
        '''What every container this deployment runs must be able to see,
        whoever's job it is: whatever the cluster needs named -- the munge
        socket and slurm.conf on Slurm, since a framework image submits the
        nodes of the flow it is driving. Baked into each shared bundle.

        🔴 **Never the data directory.** It holds the token signing key and the
        store, and every user's tree (profile §0). What one job sees is
        :meth:`job_mounts`, in a bundle of its own.
        '''
        return [str(path) for path in (self._config["container_mounts"] or [])]

    def job_mounts(self, job):
        '''What one job's node containers see: the job's own tree and its
        user's cache read-write, and the roots this server supplies read-only.
        '''
        # 🔴 Supplied roots are READ-ONLY in the job: the held copies of remote
        # sources and every private root the operator maps. A job reads what it
        # is supplied and can change none of it -- the next job gets the same
        # copy.
        #
        # ⚠️ **Every source a bundle binds must exist**, or the runtime cannot
        # start the container at all ("cannot stat"): this server's own
        # directories are made here, and an operator's root that is not there
        # is left out, and said -- a job cannot be supplied from it anyway.
        own = [self.job_root(job["user_id"], job["id"]), self.cache_dir(job["user_id"]),
               self._datadir / "sources"]
        for path in own:
            path.mkdir(parents=True, exist_ok=True)
        private = []
        for roots in (self._config["private_dataroots"] or {}).values():
            for root in roots.values():
                if os.path.isdir(root):
                    private.append((str(root), "ro"))
                else:
                    logger.warning(f"private dataroot {root} is not a directory here; "
                                   "no container is given it")
        return [(str(own[0]), "rw"), (str(own[1]), "rw"), (str(own[2]), "ro")] + private

    def framework_mounts(self, job):
        '''What the job's own process sees, beside :meth:`job_mounts`: where
        it unpacks the images its nodes run in, and where it writes their
        bundles, which no node sees.'''
        return self.job_mounts(job) + [(str(self.bundles_root()), "rw"),
                                       (str(self.job_bundles(job["id"])), "rw")]

    def job_bundles(self, job_id: str) -> Path:
        '''Where one job's bundles are: outside its tree, so that no node of
        it can rewrite what the next is started with.'''
        return self._datadir / "jobbundles" / job_id

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
        is advisory, checked again against the manifest's read while staging, and
        stored as `jobs.descriptor`.
        🔴 Strict, like every request body: an unknown member is refused, never
        ignored.
        '''
        with self._keyed(session.user_id, "create", idempotency_key):
            return self._create(session, body, idempotency_key)

    def _create(self, session, body, idempotency_key):
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
        # Authoritative, like run_hash: the server never reads a job id out of
        # the upload (surface D175).
        continuations = _continuations(body.get("continues_from"))

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
            if existing is not None and _expired_key(existing["created_at"]):
                # Forgetting a key clears its column, so the index accepts it again.
                with self._store.transaction():
                    self._store.execute("UPDATE jobs SET idempotency_key = NULL "
                                        "WHERE id = ?", (existing["id"],))
                existing = None
            if existing is not None:
                # The same key with a different body is the caller having reused
                # a key they should have rotated. Returning the first job would
                # answer a question they did not ask.
                if (existing["design"], existing["jobname"], existing["run_hash"],
                        json.loads(existing["descriptor"]),
                        self._continuations_of(existing["id"])) != \
                        (design, jobname, run_hash, descriptor, sorted(continuations)):
                    raise ProblemError(
                        "idempotency-key-reuse",
                        detail="this Idempotency-Key was used for a different request")
                # The original answer, status and body.
                return (json.loads(existing["create_reply"]) if existing["create_reply"]
                        else self.wire(existing)), 201

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

        self._check_concurrent_jobs(session.user_id)
        self._check_pending_uploads(session.user_id)
        self._check_descriptor(descriptor, requires)
        # Before anything is uploaded: every earlier result this run would
        # take, and what those results were built from.
        self._check_continuations(session.user_id, continuations)

        asked = self._look_up(declared) if declared is not None else None

        # 🔴 The job's own image, from `requires.python` alone, before anything
        # is uploaded (surface §13; database D145): whether ONE image holds the
        # python set together is only the join's to say. Node images wait for
        # the manifest's read, which is what says which tools the nodes run.
        image_id = images.job_image_for(self._store, requires)["id"] \
            if self._config["containers"] else None

        job_id = str(uuid7())
        device_id = session.device_id

        def admit():
            # 🔴 Counted again, inside the transaction that inserts: the
            # checks above answer early, and these are what hold the ceiling
            # when several creates arrive at once (`Store.admission`).
            self._check_concurrent_jobs(session.user_id)
            self._check_pending_uploads(session.user_id)
            self._store.execute(
                "INSERT INTO jobs (id, user_id, device_id, state, design, jobname, "
                "                  descriptor, idempotency_key, run_hash, "
                "                  job_identity, retention_until, upload_sources, image_id) "
                "VALUES (?, ?, ?, 'created', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, session.user_id, device_id, design, jobname,
                 json.dumps(descriptor), idempotency_key, run_hash, identity,
                 _retention(self._config.limits["job_retention_days"]),
                 json.dumps(asked) if asked else None, image_id))
            for step, index, from_job in continuations:
                self._store.execute(
                    'INSERT INTO job_continuations (job_id, step, "index", from_job_id) '
                    "VALUES (?, ?, ?, ?)", (job_id, step, index, from_job))
            self._transition(job_id, None, "created", actor=session.user_id)

        self._store.admission(admit)

        # The job object, in `created`: `upload_sources` is on it where the
        # server is asking, and absent where there is nothing to send.
        reply = self.wire(self._row(job_id))
        if idempotency_key is not None:
            with self._store.transaction():
                self._store.execute("UPDATE jobs SET create_reply = ? WHERE id = ?",
                                    (json.dumps(reply), job_id))
        return reply, 201

    ######################################################################
    # A run that starts part-way through its flow (surface D175)
    ######################################################################

    def _account_upstream(self, session, job, summary, unpacked: Path):
        '''Every node the run reads and does not run: in the archive, or
        copied from the job `continues_from` names -- and none in neither.
        Returns the nodes to copy, as ``((step, index), from_job)``.

        A node in both is taken from the archive, and an entry for a node the
        run does not read is not copied. What is copied is checked again, and
        so is what it was built from.
        '''
        continued = {(step, index): from_job
                     for step, index, from_job in self._continuations_of(job["id"])}
        copies = []
        for step, index in summary["upstream"]:
            if runspec.outputs_present(unpacked / step / index, job["design"]):
                continue
            if (step, index) not in continued:
                raise self._refuse(session, job, ProblemError(
                    "archive-rejected", reason="missing_member",
                    detail=f"the run reads the results of {step}/{index}, which it does "
                           "not run, and they are neither in the archive nor named in "
                           "continues_from"))
            copies.append(((step, index), continued[(step, index)]))
        try:
            self._check_continuations(
                job["user_id"], [(step, index, from_job) for (step, index), from_job in copies])
        except ProblemError as problem:
            raise self._refuse(session, job, problem) from None
        return copies

    def _copy_results(self, job, unpacked: Path, copies) -> None:
        '''Each node's outputs and manifest from the job that ran it, into
        ``<step>/<index>/outputs/`` -- where uploaded results land, so the run
        needs no change. The copied node gets no row and no artifacts here.

        🔴 **The archive is read as untrusted**, like every read of a job's
        tree: an upload's rules (`archive.extract`), links included, and only
        under ``outputs/``. A link to a passed-through file's home is then
        resolved from the earlier job's own archives (:meth:`_resolve_links`),
        and no bytes pass to or from the user.
        '''
        for (step, index), from_job in copies:
            held = {row["kind"]: row for row in self._store.all(
                'SELECT kind, storage_key, withheld_at FROM artifacts WHERE job_id = ? '
                "AND step = ? AND \"index\" = ? AND kind IN ('node', 'manifest') "
                "AND deleted_at IS NULL", (from_job, step, index))}
            withheld = [kind for kind, row in held.items() if row["withheld_at"]]
            if withheld:
                raise self._refuse_staging(job, ProblemError(
                    "prior-results-unavailable", step=step, index=index,
                    job_id=from_job, reason="withheld",
                    detail=f"the {withheld[0]} artifact of {step}/{index} in job "
                           f"{from_job} was withheld before it could be copied"))
            target = unpacked / step / index
            try:
                _extract_outputs(self._storage.artifact_path(held["node"]["storage_key"]),
                                 unpacked, step, index, self._config.limits)
                with gzip.open(self._storage.artifact_path(
                        held["manifest"]["storage_key"])) as source, \
                        open(target / "outputs" / f"{job['design']}.pkg.json", "wb") as out:
                    shutil.copyfileobj(source, out)
            except (KeyError, FileNotFoundError):
                raise self._refuse_staging(job, ProblemError(
                    "prior-results-unavailable", step=step, index=index, job_id=from_job,
                    reason="expired",
                    detail=f"the results of {step}/{index} in job {from_job} went before "
                           "they could be copied")) from None
            except archive.ArchiveRejected as e:
                raise _ServerFailure(f"the results of {step}/{index} in job {from_job} "
                                     f"could not be copied: {e.detail}") from None
            except OSError as e:
                raise _ServerFailure(f"this server's store did not answer the copy of "
                                     f"{step}/{index} from job {from_job}: {e}") from None
            logger.info(f"{job['id']}: copied {step}/{index} from {from_job}")

        in_place = {node for node, _ in copies} | {
            node for node in self._upstream_uploaded(job, unpacked)}
        for (step, index), from_job in copies:
            self._resolve_links(job, unpacked, (step, index), from_job, in_place)

    # How many earlier jobs a passed-through file's home is looked for through.
    CONTINUATION_DEPTH = 8

    def _upstream_uploaded(self, job, unpacked: Path):
        '''The nodes whose outputs arrived in the upload.'''
        for top in sorted(unpacked.iterdir()):
            if not top.is_dir() or top.is_symlink():
                continue
            for node in sorted(top.iterdir()):
                if (node / "outputs").is_dir() and not (node / "outputs").is_symlink() \
                        and runspec.outputs_present(node, job["design"]):
                    yield (top.name, node.name)

    def _resolve_links(self, job, unpacked: Path, node, from_job: str, in_place) -> None:
        '''Every link in a copied node's ``outputs/`` to a file whose home is
        not in place in this job's tree: the file itself, from the home node's
        archive in the earlier job (surface *Passed-through files are resolved
        while staging*).

        Where the home is copied or uploaded, the link stays. Where the earlier
        job itself took the home from another job, it has no archive of it:
        its continuations are followed to the job that ran it.
        '''
        outputs = unpacked / node[0] / node[1] / "outputs"
        for dirpath, dirnames, filenames in os.walk(outputs, followlinks=False):
            for name in sorted(dirnames + filenames):
                path = Path(dirpath) / name
                if not path.is_symlink():
                    continue
                home = _link_home(unpacked, path)
                if home is None or home[0] == node or home[0] in in_place:
                    continue
                self._place_from_home(job, path, home, from_job, depth=0)

    def _place_from_home(self, job, path: Path, home, from_job: str, depth: int) -> None:
        '''The file ``home`` names, from its node's archive in ``from_job``
        -- or through ``from_job``'s own continuations -- at ``path``, in
        place of the link.'''
        (step, index), member = home
        if depth > self.CONTINUATION_DEPTH:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="expired",
                detail=f"{step}/{index}'s results, which a copied node links to, are "
                       f"more than {self.CONTINUATION_DEPTH} jobs back"))

        row = self._store.one(
            'SELECT storage_key, withheld_at, deleted_at FROM artifacts WHERE job_id = ? '
            "AND step = ? AND \"index\" = ? AND kind = 'node'", (from_job, step, index))
        if row is None:
            earlier = self._store.one(
                'SELECT from_job_id FROM job_continuations WHERE job_id = ? AND step = ? '
                'AND "index" = ?', (from_job, step, index))
            if earlier is not None:
                return self._place_from_home(job, path, home, earlier["from_job_id"],
                                             depth + 1)
        if row is None or row["deleted_at"]:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="expired",
                detail=f"the node artifact of {step}/{index} in job {from_job}, the home "
                       "of a file a copied node links to, is gone"))
        if row["withheld_at"]:
            raise self._refuse_staging(job, ProblemError(
                "prior-results-unavailable", step=step, index=index, job_id=from_job,
                reason="withheld",
                detail=f"the node artifact of {step}/{index} in job {from_job}, the home "
                       "of a file a copied node links to, is withheld"))

        import tempfile
        try:
            with tempfile.TemporaryDirectory(dir=str(path.parent)) as scratch:
                scratch = Path(scratch)
                _extract_outputs(self._storage.artifact_path(row["storage_key"]),
                                 scratch, step, index, self._config.limits,
                                 only=member)
                found = scratch / step / index / member
                if found.is_symlink():
                    # The home's own pass-through: its home, in turn.
                    onward = _link_home(scratch, found)
                    if onward is None:
                        raise _ServerFailure(f"a link in {step}/{index} of job "
                                             f"{from_job} leads nowhere")
                    path.unlink()
                    return self._place_from_home(job, path, onward, from_job, depth + 1)
                if not found.exists():
                    raise self._refuse_staging(job, ProblemError(
                        "prior-results-unavailable", step=step, index=index,
                        job_id=from_job, reason="expired",
                        detail=f"{member} is not in the node artifact of {step}/{index} "
                               f"in job {from_job}"))
                path.unlink()
                os.replace(found, path)
        except archive.ArchiveRejected as e:
            raise _ServerFailure(f"the results of {step}/{index} in job {from_job} could "
                                 f"not be read: {e.detail}") from None
        except OSError as e:
            raise _ServerFailure(f"this server's store did not answer for {step}/{index} "
                                 f"of job {from_job}: {e}") from None

    def _skipped_upstream(self, job) -> Set[Tuple[str, str]]:
        '''The nodes skipped in the jobs this one continues from, by those jobs'
        own recorded states -- never the upload's say-so.'''
        return {(row["step"], row["index"]) for row in self._store.all(
            'SELECT n.step, n."index" FROM job_nodes n JOIN job_continuations c '
            "ON n.job_id = c.from_job_id WHERE c.job_id = ? AND n.state = 'skipped'",
            (job["id"],))}

    def _continuations_of(self, job_id: str) -> List[Tuple[str, str, str]]:
        return [(row["step"], row["index"], row["from_job_id"]) for row in self._store.all(
            'SELECT step, "index", from_job_id FROM job_continuations WHERE job_id = ? '
            'ORDER BY step, "index"', (job_id,))]

    def _check_continuations(self, user_id: str, continuations) -> None:
        '''Every entry's results are usable, and none was built from something
        nobody here may use -- at create before the upload, and again at
        submit.'''
        for step, index, from_job in continuations:
            refused = self._continuation_refused(user_id, step, index, from_job)
            if refused:
                reason, detail = refused
                raise ProblemError("prior-results-unavailable", step=step, index=index,
                                   job_id=from_job, reason=reason, detail=detail)

        # 🔴 The job's resource set includes what it copies: without this a
        # job could name a PDK the caller may use and continue from results
        # built on one they may not. This profile's gate is `denied_resources`.
        for step, index, from_job in continuations:
            for kind, name in self._resources_of(from_job):
                if self._config.denied(kind, name):
                    raise ProblemError(
                        "entitlement-denied", resource_kind=kind, resource=name,
                        detail=f"the results of {step}/{index} this job would continue "
                               f"from were built from a {kind} this deployment does not "
                               "allow")

    def _continuation_refused(self, user_id, step, index, from_job):
        '''Why one entry's results cannot be used, as (reason, detail), or None.'''
        row = self._store.one("SELECT deleted_at FROM jobs "
                              "WHERE id = ? AND user_id = ?", (from_job, user_id))
        where = f"{step}/{index} of job {from_job}"
        if row is None:
            # 🔴 One answer for none and for somebody else's: it confirms nothing.
            return "not_found", f"no job of yours has that id, for {step}/{index}"
        if row["deleted_at"]:
            return "deleted", f"job {from_job} is deleted"
        # An archived job may be continued from: `archived` is never raised.
        node = self._store.one('SELECT state FROM job_nodes WHERE job_id = ? AND step = ? '
                               'AND "index" = ?', (from_job, step, index))
        if node is not None and node["state"] == "skipped":
            # Nothing to copy: the run looks through it to what fed it.
            return None
        if node is None or node["state"] != "completed":
            return "not_completed", (f"job {from_job} did not complete {step}/{index}: a job "
                                     "that only copied a node in did not run it")
        held = {row["kind"]: row for row in self._store.all(
            'SELECT kind, deleted_at, withheld_at FROM artifacts WHERE job_id = ? '
            "AND step = ? AND \"index\" = ? AND kind IN ('node', 'manifest')",
            (from_job, step, index))}
        # On this profile the artifact holding a node's outputs is its `node`
        # archive: it keeps no `outputs` kind.
        for kind in ("node", "manifest"):
            if kind not in held or held[kind]["deleted_at"]:
                return "expired", f"the {kind} artifact of {where} is gone"
        for kind in ("node", "manifest"):
            if held[kind]["withheld_at"]:
                return "withheld", f"the {kind} artifact of {where} is withheld"
        return None

    def _resources_of(self, job_id: str) -> List[Tuple[str, str]]:
        '''What one job's results were built from: its PDK and libraries as
        its manifest's read found them, and its tools.'''
        row = self._store.one("SELECT manifest_resources, manifest_pdk, manifest_tools "
                              "FROM jobs WHERE id = ?", (job_id,))
        if row is None:
            return []
        found = [tuple(pair) for pair in json.loads(row["manifest_resources"] or "[]")]
        if not found and row["manifest_pdk"] and row["manifest_pdk"] != "none":
            found.append(("pdk", row["manifest_pdk"]))
        found += [("tool", name) for name in json.loads(row["manifest_tools"] or "[]")]
        return found

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
        '''`pending_uploads`, where numeric: a hard ceiling on the caller's
        jobs in `created` or `awaiting_input`. `null` is unenforced.'''
        ceiling = self._config.limits["pending_uploads"]
        if ceiling is None:
            return
        held = [row["id"] for row in self._store.all(
            "SELECT id FROM jobs WHERE user_id = ? "
            "AND state IN ('created', 'awaiting_input') ORDER BY created_at", (user_id,))]
        if len(held) >= ceiling:
            # Which jobs hold the slots, so the client can cancel one it abandoned.
            raise ProblemError(
                "limit-exceeded", limit="pending_uploads", job_ids=held,
                detail=f"{len(held)} jobs are already waiting for their upload",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    def _check_descriptor(self, descriptor: Dict[str, Any], requires) -> None:
        '''The early reject, on whatever is present.

        Client-asserted, so this is a hint and not a boundary -- every value is
        checked again against the manifest's read. It exists to save an upload, and it
        never refuses
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
        `software-unavailable` where the join could only say the combination
        failed.

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
                    # 🔴 A listed name is never ignored: a python name nothing
                    # here tracks is checked against what jobs would run in.
                    if bucket == images.BUCKETS["python"]:
                        self._check_untracked_python(name, asked)
                    continue

                spec = images.specifiers(asked)
                if any(images.matches(version, "reported", spec)
                       for version in said.get(name, ())):
                    continue

                # Software no image holds, SiliconCompiler's own version
                # included (surface §7), whose answer names what is available.
                if here[name] and not said.get(name):
                    detail = (f"this server has {name}, and reports no version for "
                              "it -- so nothing here can be matched against a "
                              f"version requirement. Ask for {name} without one")
                else:
                    detail = (f"this server runs {name} {', '.join(here[name])}, "
                              f"and you asked for {asked}")
                raise ProblemError(
                    "software-unavailable", reason="unavailable", detail=detail,
                    unresolved=[{"name": name, "requirement": list(asked or ()),
                                 "available": sorted(said.get(name, ()))}])

    def _check_untracked_python(self, name: str, asked) -> None:
        '''A `requires.python` name the registry does not track: refused where
        nodes run in containers, since no live image holds it, and answered
        from this server's own Python where they run on the host.'''
        from importlib import metadata

        spec = images.specifiers(asked)
        available = []
        if not self._config["containers"]:
            try:
                version = metadata.version(name)
            except metadata.PackageNotFoundError:
                version = None
            if version is not None:
                if images.matches(version, "reported", spec):
                    return
                available = [version]

        where = "no image this server runs holds it" if self._config["containers"] \
            else (f"this server runs {name} {available[0]}" if available
                  else f"this server's Python has no {name}")
        raise ProblemError(
            "software-unavailable", reason="unavailable",
            detail=f"the job needs {name} {', '.join(asked) or '(any version)'}, and {where}",
            unresolved=[{"name": name, "requirement": list(asked or ()),
                         "available": available}])

    ######################################################################
    # 14. upload-grant
    ######################################################################

    def grant(self, session, job_id: str, url_root: str,
              body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        '''Endpoint 14: a grant for the archive about to be uploaded.

        🔴 **`size_bytes` and `digest` are REQUIRED, and the first grant for
        each archive fixes both** (D125); a re-issue must repeat them. Submit
        runs only bytes matching the bound digest, so nothing written to the
        upload location afterwards changes what runs. `max_upload_bytes`
        bounds a job's archives together.
        '''
        job = self.owned(session, job_id)

        if job["state"] not in ("created", "awaiting_input"):
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} takes no upload")

        body = body if isinstance(body, dict) else {}
        _only(body, ("size_bytes", "digest"), "the grant request")
        size = body.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ProblemError("invalid-request",
                               detail="size_bytes is required: the size of the archive "
                                      "to upload")
        digest = body.get("digest")
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise ProblemError("invalid-request",
                               detail="digest is required and is 'sha256:<hex>'")

        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}")

        if job["grant_bytes"] is not None and (
                job["grant_bytes"] != size or job["grant_digest"] != digest):
            # A re-issue cannot widen -- or narrow -- what the first grant bound.
            raise ProblemError(
                "job-state-conflict",
                detail="this archive's first grant fixed its size and digest; a "
                       "re-issue must repeat both")

        expires = int(_epoch()) + grant_seconds(self._config.limits["max_upload_bytes"])
        signature = self._storage.sign_upload(job["id"], size, expires)
        ceiling = size

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET upload_key = ?, upload_location_id = ?, grant_bytes = ?, "
                "  grant_digest = ?, upload_grant_expires_at = ?, upload_revoked_at = NULL "
                "WHERE id = ?",
                (job["id"], self._config["storage_location_id"], size, digest,
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

    def submit(self, session, job_id: str, body: Dict[str, Any],
               idempotency_key: Optional[str]) -> Dict[str, Any]:
        '''Endpoint 15: `202` in `staging`, once the upload matches the digest.

        🔴 **Nothing here opens the archive** (surface §15). It is kept, the job
        stages, and extraction, the manifest's read and every check run there. A
        refusal of the request itself -- the digest, the job's state,
        `concurrent_jobs` -- leaves the job `awaiting_input` with its upload
        where the grant put it, so the client may submit again.
        '''
        with self._keyed(session.user_id, "submit", idempotency_key):
            return self._submit(session, job_id, body, idempotency_key)

    def _submit(self, session, job_id, body, idempotency_key):
        job = self.owned(session, job_id)

        if idempotency_key is not None and job["submit_idempotency_key"] == idempotency_key \
                and not _expired_key(job["submit_key_at"]):
            # The original answer, whatever the job has done since.
            return json.loads(job["submit_reply"]) if job["submit_reply"] else self.wire(job)

        if job["state"] != "awaiting_input":
            raise ProblemError(
                "job-state-conflict",
                detail=f"a job in {job['state']} cannot be submitted")

        # 🔴 The digest and nothing else: the grant fixed the size and storage
        # enforced it on the PUT.
        _only(body if isinstance(body, dict) else {}, ("digest",), "the submit request")
        digest = body.get("digest") if isinstance(body, dict) else None
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise ProblemError(
                "invalid-request",
                detail="digest is required and is 'sha256:<hex>'")

        reported = self._storage.stat_upload(job["id"])
        if reported is None:
            raise ProblemError(
                "job-state-conflict",
                detail="no upload has arrived for this job; ask for a grant and PUT to it")
        size, reported_digest = reported

        # Only bytes matching the digest the grant bound are ever extracted, so
        # nothing written to the upload location after this changes what runs.
        if reported_digest != digest or (job["grant_digest"] and job["grant_digest"] != digest):
            raise ProblemError(
                "upload-digest-mismatch",
                detail=f"storage holds {size} bytes, {reported_digest}, and this "
                       f"submit names {digest}")

        # Every archive of the job together (D125): a follow-up cannot carry
        # what the first was refused for being too large.
        ceiling = self._config.limits["max_upload_bytes"]
        if job["archives_bytes"] + size > ceiling:
            raise ProblemError(
                "upload-too-large", limit="max_upload_bytes",
                detail=f"{job['archives_bytes'] + size} bytes across this job's "
                       f"uploads, and this server accepts at most {ceiling}")

        self._check_concurrent_jobs(session.user_id)

        if idempotency_key is not None:
            other = self._store.one(
                "SELECT id, submit_key_at FROM jobs WHERE user_id = ? "
                "AND submit_idempotency_key = ? AND id <> ?",
                (session.user_id, idempotency_key, job["id"]))
            if other is not None and not _expired_key(other["submit_key_at"]):
                raise ProblemError(
                    "idempotency-key-reuse",
                    detail="this Idempotency-Key was used to submit a different job")
            if other is not None:
                with self._store.transaction():
                    self._store.execute(
                        "UPDATE jobs SET submit_idempotency_key = NULL, submit_reply = NULL "
                        "WHERE id = ?", (other["id"],))

        # 🔴 Kept from here on, as its own `input`, whatever staging finds:
        # every upload the job took can be looked at afterwards -- a refused one
        # most of all (surface D133).
        def admit():
            # 🔴 `concurrent_jobs` counted again inside the transaction that
            # moves the job into `staging`, which is what it counts, and the
            # job's own state with it: two submits cannot both take the last
            # slot (`Store.admission`). Before anything is moved, so a refusal
            # leaves the upload where the grant put it.
            if self._row(job["id"])["state"] != "awaiting_input":
                raise ProblemError(
                    "job-state-conflict",
                    detail="this job was submitted or ended meanwhile")
            self._check_concurrent_jobs(session.user_id)
            artifacts.record_upload(
                self._store, self._storage, self._config, job,
                self._storage.upload_path(job["id"]), reported_digest, size)
            self._store.execute(
                "UPDATE jobs SET archives_bytes = archives_bytes + ?, grant_bytes = NULL, "
                "  grant_digest = NULL, upload_digest = ?, upload_bytes = ?, "
                "  unpack_pending = 1, submit_idempotency_key = ?, submit_key_at = ?, "
                "  submit_reply = NULL WHERE id = ?",
                (size, digest, size, idempotency_key,
                 now() if idempotency_key is not None else None, job["id"]))
            self._transition(job["id"], "awaiting_input", "staging",
                             actor=session.user_id, state_reason="unpacking the upload")

        self._store.admission(admit)
        # Only what is left of it: an interrupted PUT's partial file.
        self._storage.discard_upload(job["id"])

        reply = self.wire(self._row(job["id"]))
        if idempotency_key is not None:
            with self._store.transaction():
                self._store.execute("UPDATE jobs SET submit_reply = ? WHERE id = ?",
                                    (json.dumps(reply), job["id"]))
        self._start_preparing(job["id"])
        return reply

    def _unpack(self, job):
        '''Staging's first phase: the newest upload extracted, the manifest
        read again over every archive, and every check re-run against the read.
        Returns ``(summary, entries)``.'''
        root = self.job_root(job["user_id"], job["id"])

        # The archive is the contents of one job directory, so it expands at
        # `<build root>/<design>/<jobname>/` -- where SiliconCompiler will look
        # for it once `option,builddir` is the job root. Both segments are the
        # DECLARED names, checked at create; the manifest's own copies are
        # checked against them, so an archive cannot name its way into another
        # job's tree.
        unpacked = root / job["design"] / job["jobname"]
        latest = self._store.one(
            "SELECT storage_key, upload_seq FROM artifacts WHERE job_id = ? "
            "AND kind = 'input' ORDER BY upload_seq DESC LIMIT 1", (job["id"],))
        follow_up = latest["upload_seq"] > 1

        # 🔴 A follow-up archive may hold only the dataroots that were asked
        # for (D124), so it cannot replace what the first archive carried after
        # the server checked it -- decided from the last read, before this
        # archive is opened.
        allowed = self._requested_members(job, root) if follow_up else None
        try:
            archive.extract(self._storage.artifact_path(latest["storage_key"]),
                            unpacked, self._config.limits, allowed=allowed)
        except archive.ArchiveRejected as rejected:
            if not follow_up:
                shutil.rmtree(root, ignore_errors=True)
            # Kept, and never opened again: see `artifacts.UNOPENED`.
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason=rejected.reason,
                detail=rejected.detail)) from None

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET unpack_pending = 0, upload_sources = NULL WHERE id = ?",
                (job["id"],))
        self._phase(job["id"], "checking the manifest")
        job = self._row(job["id"])

        # Read again over the union of every archive, never from `sources`.
        summary = self._read(job, root)
        if not follow_up:
            self._check_members(job, summary, unpacked)
        self._check_environments(None, job, summary, unpacked)
        self._check_denied(None, job, summary)
        entries = self._account(None, job, summary, unpacked)
        asked = [entry for entry in entries if entry.status == owners.ASK]
        self._check_owed(None, job, summary, asked)

        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET manifest_pdk = ?, manifest_resources = ? WHERE id = ?",
                (summary["pdk"], json.dumps([list(pair) for pair in _resources(summary)]),
                 job["id"]))
        return summary, entries

    def _check_members(self, job, summary, unpacked: Path) -> None:
        '''🔴 The first archive holds only the manifest at its root,
        `sc_collected_files/`, the Python environment, and
        `<step>/<index>/outputs/` for each node the run reads and does not
        run; anything else is `unrequested_member` (surface *What the archive
        carries, and who decides*).'''
        from siliconcompiler.remote import environment

        upstream = set(summary["upstream"])
        allowed = {f"{job['design']}.pkg.json", "sc_collected_files", environment.ROOT}

        def refuse(member):
            return self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="unrequested_member",
                detail=f"{member} is not something a first archive carries: the "
                       "manifest, sc_collected_files/, the Python environment and "
                       "the outputs of each node the run reads and does not run"))

        def real_dir(path):
            return path.is_dir() and not path.is_symlink()

        outputs = []
        for top in sorted(unpacked.iterdir()):
            if top.name in allowed:
                continue
            if not real_dir(top) or not any(step == top.name for step, _ in upstream):
                raise refuse(top.name)
            for node in sorted(top.iterdir()):
                if (top.name, node.name) not in upstream or not real_dir(node):
                    raise refuse(f"{top.name}/{node.name}")
                for member in sorted(node.iterdir()):
                    if member.name != "outputs" or not real_dir(member):
                        raise refuse(f"{top.name}/{node.name}/{member.name}")
                outputs.append(member)

        # 🔴 A link in an upstream node's `outputs/` points at a file's home in
        # another node's `outputs/` in this archive, or at its own node's: a
        # passed-through file, packed once (contract.md, *An upload keeps
        # links*). A link carries no bytes, so it counts as a member and not
        # toward the expanded size.
        homes = [os.path.realpath(str(path)) for path in outputs]
        for here in outputs:
            for dirpath, dirnames, filenames in os.walk(here, followlinks=False):
                for name in dirnames + filenames:
                    path = os.path.join(dirpath, name)
                    if not os.path.islink(path):
                        continue
                    real = os.path.realpath(path)
                    if not any(real == home or real.startswith(home + os.sep)
                               for home in homes):
                        raise self._refuse_staging(job, ProblemError(
                            "archive-rejected", reason="unrequested_member",
                            detail=f"{os.path.relpath(path, str(unpacked))} is a link "
                                   "outside the outputs of the nodes this archive "
                                   "carries"))

    ######################################################################
    # What a run's files are, and where the server's copies come from
    ######################################################################

    def _account(self, session, job, summary, unpacked: Path):
        '''Every file the manifest names, as how it reaches the run; refuse
        what nobody can supply.

        🔴 **No path the job names is read** (D112) -- see `owners.account`.
        `resource-unavailable` is raised only for what the caller could not
        send either (D127): a private dataroot this server has no copy of, a
        private design, or a path that escapes the root it is supplied under.
        '''
        entries = owners.account_records(summary["values"], unpacked / "sc_collected_files",
                                         self._supply, summary["required"])
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

    def _check_environments(self, session, job, summary, unpacked: Path) -> None:
        '''The job's Python: each node's environment file and the uploaded
        packages, while staging (surface *A node's own Python packages, built
        while staging*).

        `sc_python/packages/` is the user's own code, accepted with or without
        an environment file and never parsed. An environment file is the
        declaration that a node has a package to install, so a job carrying one
        relies on `python.env` whether or not it said so at create; each is
        held to its path -- a node the run executes -- and to the format. A
        follow-up carrying either never gets here: it is `unrequested_member`,
        since only what was asked for may arrive.
        '''
        from siliconcompiler.remote import environment

        top = unpacked / environment.ROOT
        if not top.exists():
            return

        def refuse(detail):
            return self._refuse(session, job, ProblemError(
                "archive-rejected", reason="environment_file", detail=detail))

        nodes = set(summary["nodes"])
        files = []
        for path in sorted(top.rglob("*")):
            if path.is_dir():
                continue
            name = path.relative_to(unpacked).as_posix()
            parts = name.split("/")
            if len(parts) >= 3 and parts[1] == environment.PACKAGES:
                # The user's own code, uploaded once beside the files: put on
                # the tool's PYTHONPATH, never installed, so nothing here
                # parses it.
                continue
            node = tuple(parts[2:4])
            if not (len(parts) == 5 and parts[1] == environment.NODES
                    and parts[4] == environment.FILENAME and node in nodes):
                raise refuse(f"{name} is neither {environment.path_for('<step>', '<index>')} "
                             f"for a node this run executes nor under "
                             f"{environment.packages_path()}/")
            files.append((name, path))

        if files and "python.env" not in (self._config["features"] or ()):
            raise self._refuse(session, job, ProblemError(
                "feature-unsupported", feature="python.env",
                detail="this job carries a Python environment for a node, and this "
                       "deployment does not install one"))

        for name, path in files:
            try:
                environment.parse(path.read_bytes())
            except environment.EnvironmentFileError as e:
                raise refuse(f"{name}: {e}") from None

    def _check_owed(self, session, job, summary, asked) -> None:
        '''Refuse a required value the client should have sent and did not.

        🔴 **Before anything dispatches (D129)**, rather than a node failing
        on a missing file. *Should have sent* is the design, anything local or
        editable, and anything this job already asked for; the rest the server
        can still ask for. Only a flow whose set is known is checked: without it
        there is no telling a missing file from one nothing reads.
        '''
        if summary["required"] is None:
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
                "archive-rejected", reason="missing_member",
                detail=f"the flow reads [{','.join(entry.key or ())}] of {entry.kind} "
                       f"{entry.name}{where}, {entry.path}, and the archive does "
                       "not carry it"))

    def _requested_members(self, job, root: Path):
        '''What a follow-up archive may hold: the collected files of the
        dataroots this job asked for that the flow reads, and nothing else --
        a dataroot asked for selects its required values, never all of it.

        ⚠️ **Each with the rest of its parameter**, as the client collects it
        (`owners.collection_keys`): a value asked for brings the others in its
        ``(key, step, index)``, whatever their dataroot.'''
        asked = {(item["kind"], item["name"], item["dataroot"])
                 for item in json.loads(job["upload_sources"] or "[]")}
        summary = self._stored_summary(job, root)
        records = summary["values"]
        where = [(tuple(record["key"]), record["step"], record["index"])
                 for record in records]
        private = {at for at, record in zip(where, records)
                   if record["origin"] == owners.PRIVATE}
        keys = {at for at, record in zip(where, records)
                if (record["kind"], record["name"], record["dataroot"]) in asked
                and owners.needed(at[0], summary["required"]) and at not in private}
        paths = {record["collected_path"] for at, record in zip(where, records)
                 if at in keys and record["origin"] != owners.PRIVATE}
        paths.discard(None)

        def allowed(member: str) -> bool:
            parts = member.split("/")
            if parts[0] != "sc_collected_files":
                return False
            inside = "/".join(parts[1:])
            # The collection directory, a bucket holding a requested file, the
            # file, or what a requested directory holds.
            return not inside or any(
                inside == path or inside.startswith(f"{path}/")
                or path.startswith(f"{inside}/") for path in paths)
        return allowed

    def _start_preparing(self, job_id: str) -> None:
        import threading

        with self._preparing_lock:
            if job_id in self._preparing:
                return
            self._preparing.add(job_id)
        threading.Thread(target=self._prepare, args=(job_id,), daemon=True,
                         name=f"prepare-{job_id[:8]}").start()

    def _prepare(self, job_id: str) -> None:
        '''Everything between submit and `queued`: unpack and check the
        upload, fetch what the run needs and the server does not hold, copy
        earlier results, build environments, then dispatch -- or send the job
        back asking for what could not be had.

        In parallel, a timeout per source and one deadline for the job. A
        transient failure is retried until the deadline; a permanent one --
        and whatever is still missing at the deadline -- goes back to the
        client, which has the credentials the server does not.

        🔴 A refusal found in the upload ends the job `rejected`; this server's
        own failure ends it `failed`, `staging-failed`, never `rejected`.
        '''
        import time
        from concurrent.futures import ThreadPoolExecutor, wait as futures_wait

        from siliconcompiler.remote.server.sources import Permanent, Transient

        try:
            job = self._row(job_id)
            if job is None or job["state"] != "staging":
                raise _NoLongerStaging(job_id)
            root = self.job_root(job["user_id"], job_id)
            unpacked = root / job["design"] / job["jobname"]
            if job["unpack_pending"]:
                summary, entries = self._unpack(job)
            else:
                summary = self._stored_summary(job, root)
                entries = self._account(None, job, summary, unpacked)

            wanted = {}
            for entry in entries:
                if entry.status == owners.FETCH:
                    wanted.setdefault((entry.source, entry.ref), []).append(entry)
            if wanted:
                self._phase(job_id, "fetching sources")

            timeout = self._config["fetch_timeout_seconds"]
            deadline = time.monotonic() + self._config["fetch_deadline_seconds"]
            # What only the client can send goes back with whatever fails to
            # fetch: one trip to `awaiting_input`, asking for all of it.
            failed = [(entry, "this server does not hold it and cannot fetch it")
                      for entry in entries if entry.status == owners.ASK]
            pause = 2
            while wanted:
                # 🔴 Watched rather than waited on: a cancel stops the fetch.
                pool = ThreadPoolExecutor(max_workers=4)
                tried = {key: pool.submit(self._fetch, key[0], key[1], timeout)
                         for key in wanted}
                while not all(future.done() for future in tried.values()):
                    futures_wait(list(tried.values()), timeout=1)
                    if self._row(job_id)["state"] != "staging":
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise _NoLongerStaging(job_id)
                pool.shutdown(wait=False)
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
                    if self._row(job_id)["state"] != "staging":
                        raise _NoLongerStaging(job_id)

            job = self._row(job_id)
            if job["state"] != "staging":
                raise _NoLongerStaging(job_id)

            if failed:
                self._send_back(job, failed)
                return

            # Everything in hand: a missing file in a fetched copy is refused
            # here, from `staging` -- and then it queues, and only moves on.
            entries = self._account(None, job, summary, unpacked)

            # The results of each node this run reads and does not run, from
            # the earlier job that ran it (surface D175).
            copies = self._account_upstream(None, job, summary, unpacked)
            if copies:
                self._phase(job_id, "copying earlier results")
            self._copy_results(job, unpacked, copies)

            # Each node's Python: installed here where nodes run on this host,
            # so a line that will not install rejects the job before any node
            # runs; built into an image on the one each node resolved to where
            # they run in containers -- which needs the images resolved first.
            self._install_on_host(job, summary)
            plan = self._build_environments(
                job, summary, self._resolve_images(None, job, summary))
            if self._row(job_id)["state"] != "staging":
                raise _NoLongerStaging(job_id)

            # `queued` only once the scheduler holds it.
            self._phase(job_id, "handing the job to the scheduler")
            self._dispatch(None, self._row(job_id), summary, entries, plan=plan)
        except ProblemError:
            # Already recorded on the job by `_refuse`.
            pass
        except _NoLongerStaging:
            # Cancelled while it staged: nothing holds it, so this is where its
            # `cancelled` is written.
            job = self._row(job_id)
            if job is not None and not job["scheduler_job_id"]:
                self._settle_cancelled(job)
        except _ServerFailure as e:
            self._fail_staging(job_id, str(e))
        except Exception as e:                                   # noqa: BLE001
            logger.exception(f"could not stage {job_id}")
            self._fail_staging(job_id, f"this server could not get the job ready: "
                                       f"{type(e).__name__}")
        finally:
            with self._preparing_lock:
                self._preparing.discard(job_id)
            self._store.release()

    def _fail_staging(self, job_id: str, detail: str) -> None:
        '''This server's own failure while staging: `failed`, `staging-failed`,
        with `detail` naming what failed -- and in the job-level `logs`.'''
        job = self._row(job_id)
        if job is not None and job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while it failed: what the owner did stands.
            self._settle_cancelled(job)
            return
        with self._store.transaction():
            job = self._row(job_id)
            if job is None or job["state"] != "staging":
                return
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = NULL, finished_at = ? "
                "WHERE id = ?", (ERRORS["staging-failed"].uri, now(), job_id))
            self._transition(job_id, "staging", "failed", reason=_bounded(detail))
        logger.warning(f"{job_id}: staging failed: {detail}")
        self._log_staging(self._row(job_id), detail)

    def _log_staging(self, job, detail: str) -> None:
        '''What went wrong while staging, in the job-level `logs`, scrubbed
        like `detail`: the only account a person can reach of a job that never
        ran.'''
        from siliconcompiler.remote.server.dispatch import RUN_LOG

        root = self.job_root(job["user_id"], job["id"])
        try:
            root.mkdir(parents=True, exist_ok=True)
            with open(root / RUN_LOG, "a") as f:
                f.write(f"{now()} staging failed: {bound(detail)}\n")
            with self._store.transaction():
                artifacts.collect_run_log(self._store, self._storage, self._config,
                                          job, root)
        except OSError as e:
            logger.warning(f"{job['id']}: could not keep the staging log: {e}")

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
                "UPDATE jobs SET upload_sources = ?, submit_idempotency_key = NULL, "
                "  submit_reply = NULL, submit_key_at = NULL "
                "WHERE id = ?", (json.dumps(asked), job["id"]))
            self._transition(job["id"], "staging", "awaiting_input",
                             reason=_bounded(reason))

    def _dispatch(self, session, job, summary, entries, plan=None) -> None:
        '''Resolve images, write the manifest the run will load, and hand
        the job to the scheduler. ``plan`` is the images already resolved
        while staging, with any a node's environment was built into.'''
        root = self.job_root(job["user_id"], job["id"])
        if plan is None:
            plan = self._resolve_images(session, job, summary)
        manifest = self._write_run(job, root, summary, plan, entries)

        try:
            bundle = self._framework_bundle(job, plan)
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
            raise _ServerFailure(f"this server's scheduler refused the job: {e}") from None

        if not self._record_submission(job, summary, scheduler_job_id, plan):
            # Cancelled while it was handed over: the scheduler lets it go.
            self._dispatcher.cancel(scheduler_job_id)
            raise _NoLongerStaging(job["id"])
        logger.info(f"submitted {job['id']} as {scheduler_job_id}")

    ######################################################################
    # A node's Python environment, built into an image (surface D131)
    ######################################################################

    def _environments(self, job, summary) -> Dict[Tuple[str, str], str]:
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
        for node in summary["nodes"]:
            path = unpacked / environment.path_for(*node)
            if not path.is_file():
                continue
            parsed = environment.parse(path.read_bytes())
            if parsed.pins:
                found[node] = environment.render(
                    parsed.pins,
                    header="Written by sc-server from what the job's file declared; "
                           "the file itself is never installed.")
        return found

    def _build_environments(self, job, summary, plan):
        '''``plan`` with every node that has an environment moved onto the
        image built for it -- reused where one exists for its base and file,
        built otherwise. Nodes whose files are identical share one build.

        🔴 **An environment that will not install rejects the job** from
        `staging`: `software-unavailable`, `reason: "uninstallable"`, naming
        each package and the target Python and platform. Never asked for as an
        upload -- the package could carry binaries this server cannot run.
        '''
        wanted = self._environments(job, summary)
        if not wanted:
            return plan

        nodes, refs = dict(plan.nodes), dict(plan.refs)
        done: Dict[str, Tuple[str, str]] = {}
        for node, text in sorted(wanted.items()):
            base_id = nodes.get(node)
            base_ref = refs.get(base_id) if base_id else None
            if not base_ref:
                raise _ServerFailure(f"{node[0]}/{node[1]} has no image to build its "
                                     "Python environment on")
            key = images.derivation(base_ref.split("@", 1)[1], text, _python_names(job))
            if key not in done:
                done[key] = self._derived_for(job, node, base_id, base_ref, key, text)
            image_id, ref = done[key]
            nodes[node] = image_id
            refs[image_id] = ref
        return images.Plan(plan.job, nodes, refs)

    def _install_on_host(self, job, summary) -> None:
        '''Host mode: each executed node's environment installed while the
        job stages, into its user's cache, where the node's task finds it.

        🔴 **A line that will not install rejects the job** --
        `software-unavailable`, `reason: "uninstallable"`, naming each package
        and the target Python and platform -- before any node runs. An index
        that does not answer is this server's failure: `staging-failed`.
        '''
        from siliconcompiler.remote import environment
        from siliconcompiler.remote.server import envinstall

        if self._config["containers"] or "python.env" not in (self._config["features"] or ()):
            return
        unpacked = self.job_root(job["user_id"], job["id"]) / job["design"] / job["jobname"]
        if not any((unpacked / environment.path_for(*node)).is_file()
                   for node in summary["nodes"]):
            return

        self._phase(job["id"], "installing Python environments")
        try:
            envinstall.install_all(unpacked, self.cache_dir(job["user_id"]) / "python-env",
                                   logger, summary["nodes"], constrain=_python_names(job),
                                   indexes=list(self._config["package_indexes"] or []))
        except envinstall.InstallFailed as e:
            if e.result.get("network") or e.result.get("returncode") == -1:
                raise _ServerFailure(_bounded(
                    f"the install of {e.node[0]}/{e.node[1]}'s Python environment could "
                    f"not reach an index:\n{e.result.get('tail', '')}")) from None
            raise self._refuse_staging(job, _build_refusal(e.node, e.text, e.result)) \
                from None
        if self._row(job["id"])["state"] != "staging":
            raise _NoLongerStaging(job["id"])

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
                # Where pip looks: the deployment's, never the job's.
                "indexes": list(self._config["package_indexes"] or []),
                "timeout": timeout,
                "constrain": _python_names(job),
                "comment": f"sc-server: a node's Python environment ({key[:12]})",
            }, indent=1))

            try:
                build_id = self._dispatcher.submit_build(
                    key[:12], workspace, workspace / envbuild.SPEC,
                    queue=self._config["build_queue"])
            except DispatchError as e:
                raise _ServerFailure(f"this server could not start the build of "
                                     f"{node[0]}/{node[1]}'s Python environment: {e}") \
                    from None
            logger.info(f"{job['id']}: building {node[0]}/{node[1]}'s environment "
                        f"as {build_id}")

            # 🔴 A cancel stops the build: the job leaving `staging` is a build
            # nobody is waiting for.
            result = envbuild.wait_for(
                workspace, timeout,
                alive=lambda: self._dispatcher.is_alive(build_id)
                and self._row(job["id"])["state"] == "staging",
                **self._build_wait)
            if self._row(job["id"])["state"] != "staging":
                self._dispatcher.cancel(build_id)
                raise _NoLongerStaging(job["id"])
            if result is None:
                self._dispatcher.cancel(build_id)
                log = workspace / envbuild.LOG
                tail = "\n".join(log.read_text(errors="replace").strip().splitlines()[-10:]) \
                    if log.is_file() else ""
                raise _ServerFailure(_bounded(
                    f"the build of {node[0]}/{node[1]}'s Python environment "
                    f"did not finish within {timeout}s" + (f":\n{tail}" if tail else "")))
            if not result.get("ok") and result.get("reason") != "uninstallable":
                raise _ServerFailure(_bounded(
                    f"this server could not build {node[0]}/{node[1]}'s Python "
                    f"environment: {result.get('detail') or 'the build failed'}"))
            if not result.get("ok"):
                raise self._refuse_staging(job, _build_refusal(node, text, result))
            return result
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _check_denied(self, session, job, summary) -> None:
        '''Refuse a run that uses a PDK, library or tool nobody may use.

        🔴 **After the manifest's read and before image resolution**: what the
        manifest names is only known once it is open, and *you may not use it*
        is asked before *can this server provide it* -- a denied tool this
        deployment has no image for is still a denial, and the caller should
        hear the answer that does not change when an image is added.

        ⚠️ The first one found is the one named, in the order PDK, library,
        tool, because the slug carries one `resource`. The detail says how many
        more there are, so fixing one is not followed by a surprise.

        ⚠️ **A summary that lies can evade this**, since the names are the
        read's (contract §1, *The summary cannot widen access*). That widens
        nothing here: `denied_resources` is a test stand-in for grants, and
        this profile has no controlled resources, no content index and no
        gate a summary feeds -- anyone may upload the same files anyway.
        '''
        wanted = _resources(summary) + [("tool", name) for name in summary["tools"]]

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

    def _resolve_images(self, session, job, summary):
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
            return images.Plan(None, {node: None for node in summary["nodes"]}, {})

        requires = requirements(json.loads(job["descriptor"]) or {})

        try:
            return images.plan_for_job(self._store, requires,
                                       summary["node_tools"], summary["inherits"],
                                       job_image_id=job["image_id"])
        except ProblemError as problem:
            # Its own slug, not a guessed one: `plan_for_job` refuses for more
            # than one reason and the job must record the one the caller was
            # given.
            raise self._refuse(session, job, problem) from None

    def _framework_bundle(self, job, plan) -> Optional[str]:
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
            common = images.stage_bundle(self.bundles_root(), ref, ref.split("@", 1)[1],
                                         mounts=self.container_mounts())
            # This job's own view of it, beside its nodes' bundles.
            return str(images.job_bundle(
                common, self.job_bundles(job["id"]) / Path(common).name,
                self.framework_mounts(job), drop=[str(self._datadir)]))
        except Exception as e:                                   # noqa: BLE001
            # Refused rather than dispatched without it. Dropping the image
            # silently would run the job against whatever SiliconCompiler this
            # cluster has, which is the thing the registry exists to stop --
            # and it would do it while the record said otherwise.
            raise _ServerFailure(f"this server could not unpack the image the job's "
                                 f"own process runs in: {e}") from None

    def _record_submission(self, job, summary, scheduler_job_id, plan) -> bool:
        '''`staging` to `queued`, now the scheduler holds it; False where the
        job left `staging` meanwhile, and stays as it is.'''
        with self._store.transaction():
            if self._row(job["id"])["state"] != "staging":
                return False
            self._store.execute(
                "UPDATE jobs SET manifest_flow = ?, manifest_nodes = ?, "
                "  manifest_tools = ?, manifest_pdk = ?, "
                "  scheduler_job_id = ?, image_id = ?, submitted_at = ? "
                "WHERE id = ?",
                (summary["flow"], len(summary["nodes"]),
                 json.dumps(summary["tools"]), summary["pdk"],
                 scheduler_job_id, plan.job, now(), job["id"]))
            self._transition(job["id"], "staging", "queued")

            for step, index in summary["nodes"]:
                self._store.execute(
                    'INSERT INTO job_nodes (job_id, step, "index", state, image_id) '
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (job["id"], step, index, plan.nodes.get((step, index))))
            for from_step, from_index, to_step, to_index in summary["edges"]:
                self._store.execute(
                    "INSERT INTO job_node_edges "
                    "(job_id, from_step, from_index, to_step, to_index) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (job["id"], from_step, from_index, to_step, to_index))
        return True

    def _check_concurrent_jobs(self, user_id: str) -> None:
        '''`concurrent_jobs`, where numeric: a hard ceiling on the caller's
        jobs in `staging`, `queued`, `running` or `cancelling`. `null` is
        unenforced.'''
        ceiling = self._config.limits["concurrent_jobs"]
        if ceiling is None:
            return
        active = self._store.one(
            "SELECT count(*) AS n FROM jobs WHERE user_id = ? "
            "AND state IN ('staging', 'queued', 'running', 'cancelling')", (user_id,))["n"]
        if active >= ceiling:
            raise ProblemError(
                "limit-exceeded", limit="concurrent_jobs",
                detail=f"{active} of your jobs are already running",
                headers={"Retry-After": str(self._config["poll_interval_seconds"])})

    ######################################################################
    # The manifest's read (contract §1)
    ######################################################################

    def _read(self, job, root: Path) -> Dict[str, Any]:
        '''Read the uploaded manifest -- in a process of its own, never this
        one -- and act on what the read says.

        🔴 **Contract §1, *No server process holding credentials parses a
        manifest*.** The read is `manifestread`, started contained by
        `sandbox`; what comes back is data, validated here, stored in the job
        root, and every check after it works from it. The descriptor said what
        the client believed; this is what it sent, and only this side is
        authoritative, which is why the checks run twice.

        Returns the summary, as :meth:`_summary` shapes it for the checks.
        '''
        unpacked = root / job["design"] / job["jobname"]
        if not (unpacked / f"{job['design']}.pkg.json").is_file():
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_missing",
                detail=f"the archive holds no {job['design']}.pkg.json at its root"))

        declared = requirements(json.loads(job["descriptor"]) or {})
        asked = manifestread.request(
            unpacked, job["design"], job["jobname"],
            (declared.get(images.BUCKETS["python"]) or {}).get("siliconcompiler"),
            self._skipped_upstream(job))
        try:
            raw = self._run_read(job, root, asked)
        except sandbox.Cancelled:
            raise _NoLongerStaging(job["id"]) from None
        except sandbox.ReadFailed as e:
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_invalid",
                detail=_bounded(f"the manifest has not been read: {e}"))) from None
        except OSError as e:
            raise _ServerFailure(f"this server could not start the manifest's read: "
                                 f"{e}") from None

        try:
            raw = manifestread.validate(raw)
        except manifestread.Invalid as e:
            raise self._refuse_staging(job, ProblemError(
                "archive-rejected", reason="manifest_invalid",
                detail=_bounded(f"the manifest's read returned a summary this server "
                                f"cannot use: {e}"))) from None

        contained = raw.get("contained") or {}
        logger.info(f"{job['id']}: read its manifest in {raw.get('seconds')}s"
                    + ("" if contained.get("network") else ", with no network namespace")
                    + ("" if contained.get("limits") else ", with no resource limits"))

        # 🔴 In the job root, above the tree the upload expanded into, so no
        # upload can write it: a resumed staging and a follow-up's allowed set
        # read it back.
        runspec.write_json(root / runspec.SUMMARY_FILENAME, raw)
        return self._act_on(job, raw)

    def _run_read(self, job, root: Path, asked) -> Any:
        '''The read: in the job's own image where this deployment runs jobs in
        containers, and on this host otherwise, as a subprocess of this
        server's own SiliconCompiler -- the one version it advertises, so the
        one every job resolves to (profile §5, D63).'''
        limits = dict(
            timeout=self._config["manifest_read_timeout_seconds"],
            alive=lambda: (self._row(job["id"]) or {"state": None})["state"] == "staging",
            cpu_seconds=self._config["manifest_read_cpu_seconds"],
            memory_bytes=self._config["manifest_read_memory_bytes"])
        workdir = root / sandbox.READ_DIRNAME
        if not (self._config["containers"] and job["image_id"]):
            return sandbox.run_read(asked, workdir, **limits)

        image = self._store.one("SELECT registry_ref, digest FROM images WHERE id = ?",
                                (job["image_id"],))
        ref = images.pinned_ref(image["registry_ref"], image["digest"])
        if self._dispatcher.name != "slurm":
            # The docker daemon's own container, as nodes run in here.
            try:
                return sandbox.run_read_in_image(asked, workdir, ref, **limits)
            except OSError as e:
                # 🔴 The job's image that cannot be had while staging is this
                # server's failure, not the job's (database D145).
                raise _ServerFailure(str(e)) from None

        # A bundle of the job's own image, with nothing but its tree mounted.
        try:
            common = images.stage_bundle(self.bundles_root(), ref, image["digest"],
                                         mounts=self.container_mounts())
            bundle = images.read_bundle(common, self.job_bundles(job["id"]) / "read",
                                        root / job["design"] / job["jobname"])
        except Exception as e:                                   # noqa: BLE001
            raise _ServerFailure(f"this server could not unpack the image the job's "
                                 f"manifest is read in: {e}") from None
        try:
            return sandbox.run_read_in_bundle(self._dispatcher, asked, workdir, str(bundle),
                                              queue=self._config["batch_queue"], **limits)
        except DispatchError as e:
            raise _ServerFailure(f"this server's scheduler refused the manifest's read: "
                                 f"{e}") from None

    def _stored_summary(self, job, root: Path) -> Dict[str, Any]:
        '''The summary the job's last read stored, validated again; the read
        run once more where there is none -- a job staged before one was kept.'''
        path = root / runspec.SUMMARY_FILENAME
        try:
            with open(path, "rb") as f:
                body = f.read(manifestread.MAX_SUMMARY_BYTES + 1)
            if len(body) > manifestread.MAX_SUMMARY_BYTES:
                raise ValueError("too large")
            return self._summary(manifestread.validate(json.loads(body)))
        except (OSError, ValueError):
            return self._read(job, root)

    def _act_on(self, job, raw) -> Dict[str, Any]:
        '''Refuse what the read found, in the order the checks run.'''
        outcome = raw["outcome"]
        if outcome is not None and raw["nodes"] is None:
            raise self._refuse_staging(job, _problem_from(outcome))

        nodes = raw["nodes"] or []
        if len(nodes) > self._config.limits["max_job_nodes"]:
            raise self._refuse_staging(job, ProblemError(
                "node-limit-exceeded", limit="max_job_nodes",
                detail=f"{len(nodes)} nodes, and this server runs at most "
                       f"{self._config.limits['max_job_nodes']}"))
        if outcome is not None:
            raise self._refuse_staging(job, _problem_from(outcome))

        # The read compared them; this compares what it reported.
        if (raw["design"], raw["jobname"]) != (job["design"], job["jobname"]):
            raise self._refuse_staging(job, ProblemError(
                "declared-mismatch",
                detail=f"the manifest is {raw['design']}/{raw['jobname']} and the job "
                       f"is {job['design']}/{job['jobname']}"))
        return self._summary(raw)

    @staticmethod
    def _summary(raw) -> Dict[str, Any]:
        '''A validated summary, as the checks read it.

        🔴 **The tools are this server's reading of the nodes**, never the
        summary's own list: a check that widened nothing still has no reason to
        believe a second copy of the same answer.
        '''
        nodes = [(entry["step"], entry["index"]) for entry in raw["nodes"]]
        node_tools = {(entry["step"], entry["index"]): entry["tool"] for entry in raw["nodes"]}
        edges = [tuple(edge) for edge in raw["edges"]]
        # A node that runs where its input ran follows its FIRST input
        # (`runspec.inheriting_nodes`), in the edges' order.
        before: Dict[Tuple[str, str], Tuple[str, str]] = {}
        for from_step, from_index, to_step, to_index in edges:
            before.setdefault((to_step, to_index), (from_step, from_index))
        return {
            "raw": raw,
            "flow": raw["flow"],
            "nodes": nodes,
            "edges": edges,
            "node_tools": node_tools,
            "inherits": {(entry["step"], entry["index"]):
                         before.get((entry["step"], entry["index"]))
                         for entry in raw["nodes"] if entry["inherits"]},
            "tools": sorted({tool for tool in node_tools.values() if tool}),
            "pdk": raw["pdk"],
            "libraries": list(raw["libraries"]),
            "fpga": raw["fpga"],
            # What the flow reads (D129), from the `require` the client worked
            # out and carried here; None where it could not.
            "required": ({tuple(key) for key in raw["required"]}
                         if raw["required"] is not None else None),
            "upstream": [tuple(node) for node in raw["upstream"]],
            "values": raw["values"],
        }

    def _write_run(self, job, root: Path, summary, plan, entries=()) -> Path:
        '''What the run needs from this server, as data beside the manifest;
        the manifest the run loads, which is the one uploaded.

        🔴 **Nothing here rewrites the manifest.** The runner loads it, in the
        job's own SiliconCompiler, and applies these overrides there
        (`runspec.apply_run`): the job id, the build and cache directories,
        each node's placement, the cluster, and where each dataroot is
        supplied. The list itself is `runspec.normalize`, the file both ends
        read.
        '''
        cache = self.cache_dir(job["user_id"])
        cache.mkdir(parents=True, exist_ok=True)

        # Where each node's image reaches it depends on what is scheduling: a
        # Slurm step names an unpacked bundle, and the docker scheduler pulls a
        # digest. The dispatcher is the only thing that knows which.
        placements = plan.placements()
        sources = {}

        shared = {}
        if self._dispatcher.name == "slurm":
            refs = placements
            placements = {}
            for node, ref in refs.items():
                # 🔴 The job's own bundle over the shared one: what a node sees
                # is its job's, never the data directory.
                common = images.bundle_path(self.bundles_root(), ref.split("@", 1)[1])
                bundle = str(self.job_bundles(job["id"]) / common.name)
                placements[node] = bundle
                sources[bundle] = ref
                shared[bundle] = str(common)

        # 🔴 Every dataroot points at the copy the run will actually read --
        # this job's upload, or this server's own supplied copy -- so the
        # manifest the run writes records which, and no dataroot is left
        # naming a path on the submitter's machine (D111, D112).
        unpacked = root / job["design"] / job["jobname"]
        runspec.write_run(
            root / runspec.RUN_FILENAME, job_id=job["id"], builddir=root, cachedir=cache,
            cluster=self._dispatcher.name, placements=placements,
            dataroots=runspec.dataroot_targets(entries, unpacked / "sc_collected_files"))

        # Only the bundles need a source: a digest the docker scheduler pulls
        # already says where it comes from.
        runspec.write_images(
            root / runspec.IMAGES_FILENAME,
            sources, self.container_mounts() if sources else [],
            python=_python_names(job), shared=shared,
            job_mounts=self.job_mounts(job) if sources else [],
            drop=[str(self._datadir)] if sources else [])

        return unpacked / f"{job['design']}.pkg.json"

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
            current = self._row(job["id"])
            if current["state"] != job["state"]:
                # Cancelled while staging checked it: what the owner did stands.
                raise _NoLongerStaging(job["id"])
            self._store.execute(
                "UPDATE jobs SET error_type = ?, error_members = ?, finished_at = ? "
                "WHERE id = ?",
                (problem.error.uri, _members_json(problem.members), now(), job["id"]))
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

        # 🔴 A filter repeats to OR within its key; keys AND together
        # (surface §16) -- so `?archived=true&archived=false` is both views.
        def values(name):
            if hasattr(args, "getlist"):
                given = args.getlist(name)
            else:
                given = args.get(name)
                given = given if isinstance(given, list) else [] if given is None else [given]
            return [value for value in given if value != ""]

        def any_of(sql_for, choices):
            if not choices:
                return
            where.append("(" + " OR ".join(sql_for for _ in choices) + ")")
            params.extend(choices)

        archived = {_flag(value) for value in values("archived")} or {False}
        if archived == {True}:
            where.append("archived_at IS NOT NULL")
        elif archived == {False}:
            where.append("archived_at IS NULL")

        states = values("state")
        known = {row["state"] for row in self._store.all("SELECT state FROM job_states")}
        for state in states:
            if state not in known:
                raise ProblemError("invalid-request", detail=f"no such job state: {state}")
        any_of("state = ?", states)

        terminal = {_flag(value) for value in values("terminal")}
        if terminal == {True}:
            where.append(f"state IN ({', '.join('?' * len(TERMINAL_STATES))})")
            params.extend(sorted(TERMINAL_STATES))
        elif terminal == {False}:
            where.append(f"state NOT IN ({', '.join('?' * len(TERMINAL_STATES))})")
            params.extend(sorted(TERMINAL_STATES))

        for column in ("design", "jobname"):
            any_of(f"{column} = ?", values(column))
        any_of("manifest_flow = ?", values("flow"))

        if values("project"):
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
        '''Endpoint 18. `cancelling` where work is in flight -- `staging`,
        `queued` or `running` -- and `cancelled` where there is none.

        🔴 **The write is conditional on the state it moves from**, so a job the
        scheduler has already ended stays as it is, and the `202` carries it.
        The scheduler side then writes `cancelled` once the work stops; a job
        still staging has no scheduler id, and its `cancelled` is written here,
        by the staging thread, when it stops.
        '''
        job = self.owned(session, job_id)

        if reason is not None:
            if not isinstance(reason, str) or len(reason) > MAX_REASON:
                raise ProblemError(
                    "invalid-request",
                    detail=f"reason is free text of at most {MAX_REASON} characters")

        if job["state"] in TERMINAL_STATES or job["state"] == "cancelling":
            # Idempotent: the caller's intent is already satisfied.
            return self.wire(job)

        in_flight = job["state"] in ("staging", "queued", "running")
        target = "cancelling" if in_flight else "cancelled"
        said = reason or "cancelled"

        with self._store.transaction():
            moved = self._transition_if(job["id"], job["state"], target,
                                        actor=session.user_id, reason=reason,
                                        state_reason=said)
            if moved:
                self._store.execute(
                    "UPDATE jobs SET cancel_requested_at = ? WHERE id = ?",
                    (now(), job["id"]))
                if target == "cancelled":
                    self._store.execute(
                        "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
                    self._storage.discard_upload(job["id"])

        if moved and job["scheduler_job_id"]:
            self._dispatcher.cancel(job["scheduler_job_id"],
                                    node_job_ids=self._node_job_ids(job))

        return self.wire(self._row(job["id"]))

    def _transition_if(self, job_id: str, from_state: str, to_state: str, **kwargs) -> bool:
        '''`_transition`, only where the job is still in ``from_state``.'''
        current = self._row(job_id)
        if current is None or current["state"] != from_state:
            return False
        self._transition(job_id, from_state, to_state, **kwargs)
        return True

    def whodunnit(self, session, job=None) -> str:
        """Who acted, in words: the person, by display name, and -- where it is
        their job -- that they own it. Never the device, and never an id."""
        row = self._store.one("SELECT display_name FROM users WHERE id = ?",
                              (session.user_id,))
        name = ((row["display_name"] if row else None) or "").strip()
        if job is not None and job["user_id"] == session.user_id:
            return f"{name}, its owner" if name else "its owner"
        return name or "another user"

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
        shutil.rmtree(self.job_bundles(job["id"]), ignore_errors=True)
        for path in (self.stream_index_path(job["id"]),
                     Path(f"{self.stream_index_path(job['id'])}.lock")):
            path.unlink(missing_ok=True)
        self._storage.discard_upload(job["id"])

        # 🔴 **An artifact under legal hold is never deleted** (entitlements
        # D54), by its owner or anybody: its row and its bytes stay, and the
        # rest go -- through `_unlink`, never a sweep of the job's directory,
        # which would take the held bytes with it.
        going = self._store.all(
            "SELECT id, location_id, storage_key FROM artifacts WHERE job_id = ? "
            "AND deleted_at IS NULL AND legal_hold_at IS NULL", (job["id"],))
        self._unlink(going)

        # The row stays, with `deleted_at` set: a `deleted` state was refused
        # because it would erase whether the job had completed, failed or been
        # rejected, which is the one fact you want when somebody asks where
        # their results went.
        with self._store.transaction():
            who = f"deleted by {self.whodunnit(session, job)}"
            self._store.execute(
                "UPDATE jobs SET deleted_at = ?, deleted_by = ?, delete_reason = ? "
                "WHERE id = ?", (now(), session.user_id, who, job["id"]))
            self._store.execute(
                "UPDATE artifacts SET deleted_at = ?, deleted_by = ?, "
                "  delete_reason = ? WHERE job_id = ? AND deleted_at IS NULL "
                "  AND legal_hold_at IS NULL",
                (now(), session.user_id, who, job["id"]))

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

        if job["state"] == "cancelling" and not job["scheduler_job_id"]:
            # Cancelled while staging, and no staging thread is left to write
            # its `cancelled` -- a restart in between.
            with self._preparing_lock:
                busy = job["id"] in self._preparing
            if not busy:
                self._settle_cancelled(job)
            return

        root = self.job_root(job["user_id"], job["id"])
        progress = runspec.read_progress(
            root / runspec.PROGRESS_FILENAME, root)

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
            if state == "completed":
                # 🔴 `completed` only once its artifacts are listed: a client
                # that sees it fetches them.
                self._index_node(job, step, index)

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
                'WHERE job_id = ? AND step = ? AND "index" = ? '
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (state, node.get("started_at"), node.get("finished_at"),
                 None if state == "cancelled" else runspec.exit_code(node.get("exit_code")),
                 error_type, job["id"], step, index))

            if state in TERMINAL_NODE_STATES and state != "completed":
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
                job_root / runspec.PROGRESS_FILENAME,
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
                (f"{TYPE_BASE}/run-interrupted", now(), job["id"]))

            # 🔴 A node that had STARTED did not get cancelled, it died. The
            # contract glosses `cancelled` as *the job ended before this node
            # started*, so using it for a node that was running says something
            # false about the one node somebody will look at first -- it is
            # where the work stopped. `failed` is what *started and did not
            # finish* means, and the environment ended it: `run-interrupted`.
            self._store.execute(
                "UPDATE job_nodes SET state = 'failed', error_type = ? "
                "WHERE job_id = ? AND state = 'running'",
                (f"{TYPE_BASE}/run-interrupted", job["id"]))

            # Everything the run never reached. These really did end before
            # they started.
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')", (job["id"],))
            self._transition(
                job["id"], job["state"], "failed",
                reason="the scheduler no longer has this job and the run never "
                       "recorded how it ended")

    def _settle_cancelled(self, job) -> None:
        '''A cancel that has taken effect: `cancelling` to `cancelled`, and
        every node it stopped `cancelled`, with no exit code and the cancel's
        reason. No error: nothing went wrong.'''
        with self._store.transaction():
            current = self._row(job["id"])
            if current is None or current["state"] != "cancelling":
                return
            said = current["state_reason"] or "cancelled"
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?", (now(), job["id"]))
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                "  state_reason = ? WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (said, job["id"]))
            self._transition(job["id"], "cancelling", "cancelled", reason="cancelled",
                             state_reason=said)

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
        self._record_metrics(job)

        reason = progress.get("error")
        limited = [f"{key} exceeded its {node['limit']} limit"
                   for key, node in sorted((progress.get("nodes") or {}).items())
                   if isinstance(node, dict) and node.get("limit")]
        if state == "failed" and limited:
            # A limit is `run-failed` with `detail` naming it.
            reason = "; ".join(limited + ([reason] if reason else []))

        with self._store.transaction():
            if state == "failed":
                self._store.execute(
                    "UPDATE jobs SET error_type = ? WHERE id = ?",
                    (f"{TYPE_BASE}/run-failed", job["id"]))
            self._store.execute(
                "UPDATE jobs SET finished_at = ? WHERE id = ?",
                (progress.get("finished_at") or now(), job["id"]))
            # 🔴 A terminal job has only terminal nodes: whatever the run never
            # finished ended with it.
            said = job["state_reason"] if state == "cancelled" else None
            self._store.execute(
                "UPDATE job_nodes SET state = 'cancelled', exit_code = NULL, "
                "  state_reason = ? WHERE job_id = ? "
                "AND state NOT IN ('completed', 'failed', 'skipped', 'cancelled')",
                (said, job["id"]))
            self._transition(job["id"], job["state"], state, reason=reason,
                             state_reason=said)

    def _record_metrics(self, job) -> None:
        '''Each node's metrics and records, into `job_nodes`, once, as the job
        ends: what the portal's metrics panel reads (implementation-notes §E,
        *The portal's metrics come from a table*).

        🔴 **Plain JSON, never SiliconCompiler** (contract §1, its second
        paragraph): the run's final manifest is read with `json`, under a size
        limit, and nothing read this way decides a refusal or a grant.
        '''
        root = self.job_root(job["user_id"], job["id"])
        found = _node_metrics(root / job["design"] / job["jobname"]
                              / f"{job['design']}.pkg.json")
        if not found:
            return
        with self._store.transaction():
            for (step, index), (metrics, records) in found.items():
                self._store.execute(
                    'UPDATE job_nodes SET metrics = ?, records = ? '
                    'WHERE job_id = ? AND step = ? AND "index" = ?',
                    (json.dumps(metrics), json.dumps(records), job["id"], step, index))

    def node_metrics(self, session, job_id: str, step: str, index: str):
        '''One node's metrics and records as the job's end recorded them, or
        None -- through the same ownership check as every read of a job.'''
        self.owned(session, job_id)
        row = self._store.one(
            'SELECT metrics, records FROM job_nodes WHERE job_id = ? AND step = ? '
            'AND "index" = ?', (job_id, step, index))
        if row is None:
            return None
        return {"metrics": json.loads(row["metrics"]) if row["metrics"] else None,
                "records": json.loads(row["records"]) if row["records"] else None}

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
        '''Endpoint 20 for one node: whether its live stream may be opened.

        🔴 **`/logs` is live output only** (surface §20). A running node
        streams; a finished one streams too, and its stream ends at once
        naming its `logs` artifact, which is fetched through endpoint 22. A
        node not started is `409 not-ready`, and a finished node that kept no
        log is `404`. Returns the node.
        '''
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="this job's data was deleted")

        if surface == "api" and "logs.stream" not in self._config["features"]:
            raise ProblemError(
                "feature-unsupported", feature="logs.stream",
                detail=_WITHOUT["logs.stream"])

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

        if node["state"] in TERMINAL_NODE_STATES:
            self._index_node(job, step, index)
            row = self._store.one(
                "SELECT * FROM artifacts WHERE job_id = ? AND step = ? "
                'AND "index" = ? AND kind = \'logs\' AND deleted_at IS NULL '
                "ORDER BY created_at LIMIT 1", (job["id"], step, index))
            if row is None:
                raise ProblemError("not-found", detail=f"no log was kept for {step}/{index}")
            # The stream names this artifact: a caller who could not fetch it
            # is not handed it by asking for the log.
            self._refuse_by_ladder(row, surface)

        return node

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
        for feature in ("logs.stream", "logs.stream.job"):
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
                    actor: Optional[str] = None, reason: Optional[str] = None,
                    state_reason: Optional[str] = None) -> None:
        # `state_reason` describes the state being entered, so every move resets it.
        self._store.execute(
            "UPDATE jobs SET state = ?, state_changed_at = ?, state_reason = ? WHERE id = ?",
            (to_state, now(), _bounded(state_reason, MAX_REASON) if state_reason else None,
             job_id))
        self._store.execute(
            "INSERT INTO job_state_transitions "
            "(job_id, from_state, to_state, actor_user_id, reason) VALUES (?, ?, ?, ?, ?)",
            (job_id, from_state, to_state, actor, reason))

    def _phase(self, job_id: str, what: str) -> None:
        '''The staging phase, as the job's `state_reason`.'''
        with self._store.transaction():
            self._store.execute(
                "UPDATE jobs SET state_reason = ? WHERE id = ? AND state = 'staging'",
                (what, job_id))

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
            # The user id is what GET /v1/me returns, so a client compares it;
            # the name is display only. Nothing here verifies who anybody is.
            "owner": {"id": job["user_id"], "name": self._display_name(job["user_id"])},
            "project": None,
            "created_at": job["created_at"],
            "submitted_at": job["submitted_at"],
            "started_at": job["started_at"],
            "finished_at": job["finished_at"],
            "archived_at": job["archived_at"],
            "deleted_at": job["deleted_at"],
            # Nothing deletes a job for retention, so a deleted job was removed.
            "deleted_cause": "removed" if job["deleted_at"] else None,
            "delete_reason": job["delete_reason"] if job["deleted_at"] else None,
            "error": _error(job["error_type"], self._why(job), job["error_members"])
            if job["state"] in ("failed", "rejected") else None,
        }
        if job["state_reason"] and body["error"] is None:
            body["state_reason"] = bound(job["state_reason"])

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

        # Echoed, and absent where the run continues from nothing.
        continued = self._continuations_of(job["id"])
        if continued:
            body["continues_from"] = [{"step": step, "index": index, "job_id": from_job}
                                      for step, index, from_job in continued]

        # 🔴 Present only while the server is asking -- in `created` or
        # `awaiting_input` -- and never `[]` (D127): what to send, and nothing
        # else.
        if job["state"] in ("created", "awaiting_input") and job["upload_sources"]:
            asking = json.loads(job["upload_sources"])
            if asking:
                body["upload_sources"] = asking

        rows = self._store.all(
            'SELECT step, "index", state, started_at, finished_at, exit_code, error_type, '
            'state_reason FROM job_nodes WHERE job_id = ? ORDER BY step, "index"',
            (job["id"],))

        if nodes:
            body["nodes"] = []
            for row in rows:
                node = {
                    "step": row["step"],
                    "index": row["index"],
                    "state": row["state"],
                    "terminal": row["state"] in TERMINAL_NODE_STATES,
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "exit_code": row["exit_code"],
                    "error_type": row["error_type"],
                }
                if row["state_reason"] and not row["error_type"]:
                    node["state_reason"] = bound(row["state_reason"])
                body["nodes"].append(node)

        def count(state):
            return sum(1 for row in rows if row["state"] == state)

        body["progress"] = {
            "total_count": len(rows),
            "completed_count": count("completed"),
            "failed_count": count("failed"),
            "skipped_count": count("skipped"),
            "cancelled_count": count("cancelled"),
        }
        return body

    def _display_name(self, user_id: str) -> str:
        row = self._store.one("SELECT display_name FROM users WHERE id = ?", (user_id,))
        return (row["display_name"] if row else None) or user_id


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
CREATE_MEMBERS = ("design", "jobname", "project", "descriptor", "run_hash", "continues_from")
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


def _extract_outputs(archive_path: Path, tree: Path, step: str, index: str, limits,
                     only: Optional[str] = None) -> None:
    '''The ``outputs/`` of a node archive -- or the one member ``only``
    names -- into ``tree``, at ``<step>/<index>/``, under an upload's rules:
    its links kept, bounded by the job's tree rather than the node's.'''
    def wanted(name):
        if only is not None:
            return name == only or only.startswith(f"{name}/") or name.startswith(f"{only}/")
        return name == "outputs" or name.startswith("outputs/")

    tree.mkdir(parents=True, exist_ok=True)
    archive.extract(archive_path, tree, limits, prefix=f"{step}/{index}", select=wanted)


def _link_home(tree: Path, link: Path):
    '''Where a link under ``tree`` points, as ``((step, index), member)``
    with ``member`` relative to that node -- or None where it is not a node's
    ``outputs/``.'''
    target = os.readlink(link)
    if os.path.isabs(target):
        return None
    joined = os.path.normpath(os.path.join(os.path.dirname(os.path.relpath(link, tree)),
                                           target))
    parts = joined.replace(os.sep, "/").split("/")
    if len(parts) < 4 or parts[2] != "outputs" or os.pardir in parts:
        return None
    return (parts[0], parts[1]), "/".join(parts[2:])


def _continuations(value) -> List[Tuple[str, str, str]]:
    '''`continues_from`: a list of `{step, index, job_id}`, one per node.'''
    import uuid

    if value is None:
        return []
    if not isinstance(value, list):
        raise ProblemError("invalid-request",
                           detail="continues_from is a list of {step, index, job_id}")
    found, seen = [], set()
    for entry in value:
        if not isinstance(entry, dict):
            raise ProblemError("invalid-request",
                               detail="each continues_from entry is {step, index, job_id}")
        _only(entry, ("step", "index", "job_id"), "a continues_from entry")
        step, index, job = entry.get("step"), entry.get("index"), entry.get("job_id")
        if not all(isinstance(value, str) and value for value in (step, index, job)):
            raise ProblemError("invalid-request",
                               detail="each continues_from entry names a step, an index "
                                      "and a job_id")
        try:
            uuid.UUID(job)
        except ValueError:
            raise ProblemError("invalid-request",
                               detail=f"continues_from names {job!r}, which is not a job "
                                      "id") from None
        try:
            # The same node-name check SiliconCompiler applies to a flow.
            Flowgraph.check_node_name(step, index)
        except ValueError as e:
            raise ProblemError("invalid-request", detail=f"continues_from: {e}") from None
        if (step, index) in seen:
            raise ProblemError("invalid-request",
                               detail=f"two continues_from entries name {step}/{index}")
        seen.add((step, index))
        found.append((step, index, job))
    return found


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


def _resources(summary) -> List[Tuple[str, str]]:
    '''The PDK, libraries and FPGA device a job's flow needs, as
    ``(resource_kind, name)``, in the order a refusal names them.'''
    return (([("pdk", summary["pdk"])] if summary["pdk"] != "none" else []) +
            [("library", name) for name in summary["libraries"]] +
            ([("fpga", summary["fpga"])] if summary.get("fpga") else []))


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


class _ServerFailure(Exception):
    '''This server's own failure while staging: `staging-failed`, its message
    the `detail`.'''


# The run's final manifest, read once as plain JSON for its metrics: larger
# than this is left unread, since the panel is not worth parsing gigabytes.
METRICS_MANIFEST_BYTES = 256 * 1024 * 1024
# Each value kept for the panel, bounded as `detail` is.
_METRIC_VALUE_CHARS = 1000


def _node_metrics(manifest: Path) -> Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]]:
    '''``{(step, index): (metrics, records)}`` out of a run's final manifest,
    read as plain JSON. Empty where there is none, or it is too large or not
    JSON.'''
    try:
        if manifest.stat().st_size > METRICS_MANIFEST_BYTES:
            logger.info(f"{manifest} is too large to read its metrics from")
            return {}
        with open(manifest, "rb") as f:
            body = json.loads(f.read(METRICS_MANIFEST_BYTES + 1))
    except (OSError, ValueError):
        return {}
    if not isinstance(body, dict):
        return {}

    def value_of(held):
        value = held.get("value") if isinstance(held, dict) else None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        text = json.dumps(value) if not isinstance(value, str) else value
        return text[:_METRIC_VALUE_CHARS]

    found: Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    for section, slot in (("metric", 0), ("record", 1)):
        params = body.get(section)
        if not isinstance(params, dict):
            continue
        for name, param in params.items():
            if name.startswith("__") or not isinstance(param, dict):
                continue
            nodes = param.get("node")
            if not isinstance(nodes, dict):
                continue
            for step, indexes in nodes.items():
                if not isinstance(indexes, dict) or step in ("global", "default"):
                    continue
                for index, held in indexes.items():
                    value = value_of(held)
                    if value is None or index in ("global", "default"):
                        continue
                    found.setdefault((str(step), str(index)), ({}, {}))[slot][name] = value
    return found


def _problem_from(outcome: Dict[str, Any]) -> ProblemError:
    '''The refusal a read reported, with only the members its type carries.

    🔴 **A read's members are written by whatever the manifest made the read
    do**, so each is taken by name and shape, never passed through: a member
    called `status` or `type` would otherwise be a field of the problem body.
    '''
    members: Dict[str, Any] = {}
    given = outcome.get("members") or {}
    if outcome["type"] == "software-unavailable":
        members["unresolved"] = [
            {"name": str(item.get("name"))[:manifestread.MAX_NAME],
             "requirement": [], "available": []}
            for item in (given.get("unresolved") or [])[:100] if isinstance(item, dict)]
    if outcome["type"] == "resource-unresolved":
        kind = given.get("resource_kind")
        members["resource_kind"] = kind if kind in owners.RESOURCE_KINDS else "pdk"
    if outcome.get("reason"):
        members["reason"] = outcome["reason"]
    return ProblemError(outcome["type"], detail=_bounded(outcome.get("detail") or ""),
                        **members)


def _build_refusal(node, text: str, result: Dict[str, Any]) -> ProblemError:
    '''What a failed environment build tells the job's owner.'''
    from siliconcompiler.remote import environment

    where = f"{node[0]}/{node[1]}"
    target = f"{result.get('python') or 'its Python'} ({result.get('version') or '?'}) " \
             f"on {result.get('platform') or 'its platform'}"

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


def _expired_key(bound_at: Optional[str]) -> bool:
    '''Whether a key bound at ``bound_at`` is past the time it is honoured.'''
    return bool(bound_at) and bound_at < _ago(IDEMPOTENCY_SECONDS)


def _error(error_type: Optional[str],
           detail: Optional[str] = None,
           members: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
    registered = ERRORS.get(slug)
    title = registered.title if registered else "The job failed"

    body = {"type": error_type, "title": title}
    # The registry's status, and none for a type that is never a response.
    if registered is not None and registered.status is not None:
        body["status"] = registered.status
    # Prose that only repeats the slug is not prose: the slug is already the
    # `type`, and a client branches on that.
    if detail and detail != slug:
        body["detail"] = bound(detail)
    if members:
        for name, value in json.loads(members).items():
            body.setdefault(name, value)
    return body


def _members_json(members: Dict[str, Any]) -> Optional[str]:
    '''A refusal's extension members, for the job's `error` to carry.'''
    return json.dumps(members, sort_keys=True) if members else None


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
