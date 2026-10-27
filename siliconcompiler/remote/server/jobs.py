'''
The job path: create, upload, submit, stage, run, cancel, delete.

Every state change goes through :meth:`Jobs.move`, a conditional ``UPDATE``, so
two threads cannot both end a job or record a transition twice. A job's state
is advanced from what the run reports when the job is read (:meth:`Jobs.reconcile`).
What the run finished is archived on a thread of the job's own, and recorded
finished only once its artifacts exist, so a read never waits on the archiving.
'''

import base64
import copy
import json
import logging
import re
import shutil
import threading
import time
import uuid
import warnings

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler.remote import manifests
from siliconcompiler.remote.runflow import runtime_nodes
from siliconcompiler.remote.server import config
from siliconcompiler.remote.server.errors import ProblemError, problem
from siliconcompiler.remote.server.outputs import artifacts
from siliconcompiler.remote.server.running import runspec
from siliconcompiler.remote.server.running.dispatch import DispatchError, dispatcher_for
from siliconcompiler.remote.server.staging.archive import ArchiveRejected, extract
from siliconcompiler.remote.server.state.storage import Storage
from siliconcompiler.remote.server.state.store import Store, iso
from siliconcompiler.scheduler.slurm import SlurmSchedulerNode
from siliconcompiler.schema import SCHEMA_VERSION, BaseSchema

__all__ = ["Jobs", "RETRY_AFTER"]


logger = logging.getLogger("sc-server")

TERMINAL = ("completed", "failed", "rejected", "cancelled", "abandoned")
# Counted against `concurrent_jobs`.
ACTIVE = ("staging", "queued", "running", "cancelling")
NODE_TERMINAL = ("completed", "failed", "skipped", "cancelled")

GRANT_SECONDS = 3600
RETRY_AFTER = 1
MAX_REASON = 300

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _marks(values) -> str:
    return ", ".join("?" * len(values))


class Jobs:
    def __init__(self, store: Store, datadir, cluster: str):
        self.store = store
        self.datadir = Path(datadir)
        self.cluster = cluster
        self.storage = Storage(datadir)
        self.dispatcher = dispatcher_for(cluster)
        # Jobs with a staging thread, an upload arriving, or a collecting thread,
        # in this process.
        self._staging = set()
        self._receiving = set()
        self._collecting = set()
        self._claim = threading.Lock()

    def root(self, user_id: str, job_id: str) -> Path:
        '''The job's build directory, where its results stay.'''
        return self.datadir / "users" / user_id / "builds" / job_id

    def row(self, job_id: str):
        return self.store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def owned(self, session, job_id: str):
        '''The caller's job; anyone else's is not found.'''
        job = self.store.one("SELECT * FROM jobs WHERE id = ? AND user_id = ?",
                             (job_id, session.user_id))
        if job is None:
            raise ProblemError("not-found", detail="no such job")
        return job

    def move(self, job_id: str, sources: Tuple[str, ...], state: str,
             reason: Optional[str] = None, cap: Optional[int] = None, **columns) -> bool:
        '''Move a job to ``state`` if it is in one of ``sources``, and record it.
        False means it was not, and nothing changed. With ``cap``, a move that would
        leave its owner more than that many active jobs is refused and undone, in
        the same transaction, so two moves cannot both pass the count.

        A terminal state closes the nodes still open: a running one failed with a
        failed job, the rest never ran.
        '''
        timestamp = time.time()
        columns["state"] = state
        if state in TERMINAL:
            columns.setdefault("finished_at", timestamp)

        with self.store.transaction():
            moved = self.store.execute(
                f"UPDATE jobs SET {', '.join(f'{name} = ?' for name in columns)} "
                f"WHERE id = ? AND state IN ({_marks(sources)})",
                (*columns.values(), job_id, *sources)).rowcount
            if not moved:
                return False

            if cap is not None:
                held = self.store.one(
                    f"SELECT count(*) AS n FROM jobs WHERE state IN ({_marks(ACTIVE)}) AND "
                    "user_id = (SELECT user_id FROM jobs WHERE id = ?)",
                    (*ACTIVE, job_id))["n"] - 1
                if held >= cap:
                    raise ProblemError("limit-exceeded", limit="concurrent_jobs",
                                       headers={"Retry-After": "5"},
                                       detail=f"{held} of this account's jobs are already "
                                              "running")

            self.store.execute("INSERT INTO job_transitions (job_id, state, at, reason) "
                               "VALUES (?, ?, ?, ?)", (job_id, state, timestamp, reason))
            if state in TERMINAL:
                self.store.execute(
                    "UPDATE job_nodes SET finished_at = ?, state = "
                    "CASE WHEN state = 'running' AND ? THEN 'failed' ELSE 'cancelled' END "
                    f"WHERE job_id = ? AND state NOT IN ({_marks(NODE_TERMINAL)})",
                    (timestamp, state == "failed", job_id, *NODE_TERMINAL))
        return True

    def create(self, session, body: Dict[str, Any], key: Optional[str]) -> Dict[str, Any]:
        for name in ("design", "jobname"):
            value = body.get(name)
            if not isinstance(value, str) or value in ("", ".", "..") \
                    or re.search(r"[/\\\x00]", value):
                raise ProblemError("invalid-request", detail=f"{name} is required and "
                                   "names a directory, so it holds no separator")

        # Remote sources are fetched by the run itself, and continuing needs the
        # earlier job's results on this server's disk.
        entry = next(iter(body.get("continues_from") or []), None)
        if entry:
            raise ProblemError(
                "prior-results-unavailable", reason="unsupported",
                detail="this server runs every node of a flow in one job",
                **{name: entry.get(name) for name in ("step", "index", "job_id")
                   if isinstance(entry, dict) and isinstance(entry.get(name), str)})
        needs = (body.get("descriptor") or {}).get("needs") or []
        if body.get("python_packages"):
            needs = ["python.env", *needs]
        for need in needs:
            if need not in config.FEATURES:
                raise ProblemError("feature-unsupported", feature=need,
                                   detail=f"this deployment does not offer {need}")

        job_id = str(uuid.uuid4())
        with self.store.transaction():
            held = key and self.store.one(
                "SELECT id FROM jobs WHERE user_id = ? AND idempotency_key = ?",
                (session.user_id, key))
            if held:
                job_id = held["id"]
            else:
                timestamp = time.time()
                self.store.execute(
                    "INSERT INTO jobs (id, user_id, design, jobname, state, idempotency_key, "
                    "created_at, active_at) VALUES (?, ?, ?, ?, 'created', ?, ?, ?)",
                    (job_id, session.user_id, body["design"], body["jobname"], key,
                     timestamp, timestamp))
                self.store.execute(
                    "INSERT INTO job_transitions (job_id, state, at) VALUES (?, 'created', ?)",
                    (job_id, time.time()))
        return self.wire(self.row(job_id))

    def grant(self, session, job_id: str, body: Dict[str, Any], origin: str):
        job = self.owned(session, job_id)
        if job["state"] != "created":
            raise ProblemError("job-state-conflict", detail="this job takes no upload")

        size, digest = body.get("size_bytes"), body.get("digest")
        if not isinstance(size, int) or isinstance(size, bool) or size < 1 \
                or not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise ProblemError("invalid-request", detail="size_bytes is a positive integer "
                               "and digest is sha256:<64 hex digits>")
        if size > config.LIMITS["max_upload_bytes"]:
            raise ProblemError("upload-too-large", limit="max_upload_bytes",
                               detail=f"{size} bytes, and this server takes at most "
                                      f"{config.LIMITS['max_upload_bytes']}")

        # The first grant fixes both; a re-issue may not widen them.
        if job["upload_size"] is None:
            self.store.execute("UPDATE jobs SET upload_size = ?, upload_digest = ? "
                               "WHERE id = ? AND upload_size IS NULL", (size, digest, job_id))
        elif (job["upload_size"], job["upload_digest"]) != (size, digest):
            raise ProblemError("job-state-conflict",
                               detail="a re-issued grant repeats the first one's size and digest")

        self._touch(job_id)
        expires = int(time.time()) + GRANT_SECONDS
        signature = self.storage.sign("upload", job_id, size, expires)
        return {"method": "PUT",
                "url": f"{origin}/storage/upload/{job_id}"
                       f"?size={size}&expires={expires}&sig={signature}",
                "headers": {"content-length": str(size)},
                "expires_at": iso(expires)}

    def receive(self, job_id: str, args, stream) -> None:
        '''The signed ``PUT``: the signature names the job and the byte count.'''
        size, expires = args.get("size", ""), args.get("expires", "")
        if not self.storage.verify(args.get("sig"), "upload", job_id, size, expires) \
                or time.time() > int(expires):
            raise ProblemError("invalid-request", detail="the upload grant is not valid")

        job = self.row(job_id)
        if job is None or job["state"] != "created":
            raise ProblemError("job-state-conflict", detail="this job takes no upload")

        self._receiving.add(job_id)
        try:
            # Kept for submit, which a client waiting for a slot repeats every few seconds.
            self.store.execute("UPDATE jobs SET received_digest = ? WHERE id = ?",
                               (self.storage.receive(job_id, stream, int(size)), job_id))
        except OverflowError as e:
            raise ProblemError("upload-too-large", detail=str(e)) from None
        except ValueError as e:
            raise ProblemError("invalid-request", detail=str(e)) from None
        finally:
            self._touch(job_id)
            self._receiving.discard(job_id)

    def _touch(self, job_id: str) -> None:
        '''The client is still at work on a job it has not submitted.'''
        self.store.execute("UPDATE jobs SET active_at = ? WHERE id = ?", (time.time(), job_id))

    def submit(self, session, job_id: str) -> Dict[str, Any]:
        job = self.owned(session, job_id)
        if job["state"] != "created" or not self.storage.upload_path(job_id).is_file():
            raise ProblemError("job-state-conflict", detail="this job holds no upload to submit")

        # Of the archive, the digest alone, and before anything is extracted.
        if job["received_digest"] != job["upload_digest"]:
            raise ProblemError("upload-digest-mismatch",
                               detail="the upload is not the one its grant bound")

        # Before the cap: a submit waiting for a slot keeps its job.
        self._touch(job_id)
        if not self.move(job_id, ("created",), "staging", submitted_at=time.time(),
                         cap=config.LIMITS["concurrent_jobs"]):
            raise ProblemError("job-state-conflict", detail="this job was already submitted")

        self._staging.add(job_id)
        threading.Thread(target=self._stage, args=(job_id,), daemon=True).start()
        return self.wire(self.row(job_id))

    def _stage(self, job_id: str) -> None:
        '''Extract, read the manifest and dispatch, off the request.'''
        job = self.row(job_id)
        try:
            try:
                self._prepare(job)
            except ArchiveRejected as e:
                raise ProblemError("archive-rejected", reason=e.reason,
                                   detail=e.detail) from None
        except ProblemError as e:
            if self.move(job_id, ("staging",), "rejected", error=json.dumps(e.body())):
                shutil.rmtree(self.root(job["user_id"], job_id), ignore_errors=True)
        except Exception as e:                                   # noqa: BLE001
            logger.exception(f"staging {job_id} failed")
            detail = str(e) if isinstance(e, DispatchError) else type(e).__name__
            self.move(job_id, ("staging",), "failed",
                      error=json.dumps(problem("staging-failed", detail=detail)))
        finally:
            self.storage.discard(job_id)
            self._staging.discard(job_id)
            self.store.release()

    def _staging_over(self, job_id: str) -> bool:
        return self.row(job_id)["state"] != "staging"

    def _prepare(self, job) -> None:
        job_id, design, jobname = job["id"], job["design"], job["jobname"]
        root = self.root(job["user_id"], job_id)
        tree = root / design / jobname

        extract(self.storage.upload_path(job_id), tree, config.LIMITS)
        manifest = tree / f"{design}.pkg.json"
        if self._staging_over(job_id):
            return
        if not manifest.is_file():
            raise ProblemError("archive-rejected", reason="missing_manifest",
                               detail=f"the archive holds no {design}.pkg.json at its root")

        project = self._read(manifest)
        if (project.name, project.option.get_jobname()) != (design, jobname):
            raise ProblemError(
                "declared-mismatch",
                detail=f"the manifest is {project.name}/{project.option.get_jobname()} and "
                       f"the job is {design}/{jobname}")

        nodes = runtime_nodes(project)
        if len(nodes) > config.LIMITS["max_job_nodes"]:
            raise ProblemError("node-limit-exceeded", limit="max_job_nodes",
                               detail=f"{len(nodes)} nodes, and this server runs at most "
                                      f"{config.LIMITS['max_job_nodes']}")

        with self.store.transaction():
            self.store.execute("UPDATE jobs SET flow = ? WHERE id = ?",
                               (project.option.get_flow(), job_id))
            for step, index in nodes:
                self.store.execute("INSERT OR IGNORE INTO job_nodes (job_id, step, idx, state) "
                                   "VALUES (?, ?, ?, 'pending')", (job_id, step, index))

        # One cache for every user: jobs run as the server, so nothing gains
        # from a copy of each PDK per user.
        cache = self.datadir / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        runspec.write_json(root / runspec.RUN_FILENAME, {
            "job_id": job_id, "builddir": str(root), "cachedir": str(cache),
            "cluster": self.cluster})

        if self._staging_over(job_id):
            return
        scheduler_id = self.dispatcher.submit(job_id, root, manifest)
        # Stored even if a cancel came meanwhile, so it can be found and stopped.
        self.store.execute("UPDATE jobs SET scheduler_job_id = ? WHERE id = ?",
                           (scheduler_id, job_id))
        if not self.move(job_id, ("staging",), "queued"):
            self.dispatcher.cancel(scheduler_id, self._node_names(job_id))

    @staticmethod
    def _read(manifest: Path):
        '''The uploaded manifest as a project, refused if newer than this schema.'''
        try:
            cfg = BaseSchema._read_manifest(str(manifest))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # On a copy: reading the version consumes it.
                found = BaseSchema._resolve_version(
                    {BaseSchema._version_key: copy.deepcopy(cfg.get(BaseSchema._version_key))})
        except Exception:                                        # noqa: BLE001
            raise ProblemError("archive-rejected", reason="invalid_manifest",
                               detail="the manifest cannot be read") from None

        if found > tuple(int(part) for part in SCHEMA_VERSION.split(".")):
            raise ProblemError(
                "software-unavailable", reason="unavailable",
                detail=f"the manifest's schema is {'.'.join(map(str, found))} and this "
                       f"server's is {SCHEMA_VERSION}")
        try:
            return manifests.read(cfg=cfg)
        except Exception:                                        # noqa: BLE001
            raise ProblemError("archive-rejected", reason="invalid_manifest",
                               detail="the manifest cannot be read") from None

    def reconcile(self, job) -> None:
        '''Advance a job from what is known of its run.'''
        if job["state"] not in TERMINAL:
            self._advance(job)

    def _collect_later(self, job_id: str, alive: bool) -> None:
        '''Start the job's collecting thread, unless one is running.'''
        with self._claim:
            if job_id in self._collecting:
                return
            self._collecting.add(job_id)
        threading.Thread(target=self._collect, args=(job_id, alive), daemon=True).start()

    def _collect(self, job_id: str, alive: bool) -> None:
        '''Make the artifacts of what the run has finished, and only then record it
        finished, since a client fetches what it sees terminal. Once the run is over,
        that is every node and the job's own, and then the job ends. Idempotent, so
        a restart that lost this thread loses nothing: the next read starts it again.'''
        try:
            job = self.row(job_id)
            # A read from before the job ended can ask again.
            if job["state"] in TERMINAL:
                return
            progress = self._progress(job)
            over = not alive or progress.get("state") in ("completed", "failed")
            nodes = {name: node for name, node in (progress.get("nodes") or {}).items()
                     if over or node.get("state") in NODE_TERMINAL}
            # Over, every node: one the run left open may still have kept a log.
            archived = [(row["step"], row["idx"]) for row in self.store.all(
                "SELECT step, idx FROM job_nodes WHERE job_id = ?", (job_id,))
                if over or f"{row['step']}/{row['idx']}" in nodes]
            artifacts.collect(self.store, self.storage.artifact_dir(job_id),
                              self.root(job["user_id"], job_id) / job["design"] / job["jobname"],
                              job, archived, over)
            self._sync_nodes(job_id, nodes)
            if over:
                self._end(job, progress)
        except Exception:                                        # noqa: BLE001
            logger.exception(f"collecting {job_id} failed")
        finally:
            self._collecting.discard(job_id)
            self.store.release()

    def _progress(self, job) -> Dict[str, Any]:
        return runspec.read_json(
            self.root(job["user_id"], job["id"]) / runspec.PROGRESS_FILENAME) or {}

    def _advance(self, job) -> None:
        job_id, state = job["id"], job["state"]
        if state == "created":
            if job_id not in self._receiving and \
                    time.time() - job["active_at"] > config.LIMITS["abandon_after_seconds"]:
                self.move(job_id, ("created",), "abandoned", reason="not submitted in time")
                self.storage.discard(job_id)
            return

        scheduler_id = job["scheduler_job_id"]
        if state == "staging" or scheduler_id is None:
            # A staging thread this process lost, as a restart does.
            if job_id not in self._staging:
                if state == "cancelling":
                    self.move(job_id, ("cancelling",), "cancelled", reason=self._reason(job_id))
                else:
                    self.move(job_id, ("staging",), "failed", error=json.dumps(problem(
                        "staging-failed", detail="staging stopped before it finished")))
            return

        # Alive first: a run that is gone has written its last progress.
        alive = self.dispatcher.is_alive(scheduler_id)
        progress = self._progress(job)
        nodes = progress.get("nodes") or {}
        done = {name for name, node in nodes.items() if node.get("state") in NODE_TERMINAL}
        # What the run finished is recorded by the thread that archives it.
        self._sync_nodes(job_id, {name: node for name, node in nodes.items()
                                  if name not in done})
        still_open = {f"{row['step']}/{row['idx']}" for row in self.store.all(
            f"SELECT step, idx FROM job_nodes WHERE job_id = ? AND state NOT IN "
            f"({_marks(NODE_TERMINAL)})", (job_id, *NODE_TERMINAL))}

        over = not alive or progress.get("state") in ("completed", "failed")
        if over or done & still_open:
            self._collect_later(job_id, alive)
        if not over and progress.get("state") == "running":
            self.move(job_id, ("queued",), "running", started_at=progress.get("started_at"))

    def _end(self, job, progress: Dict[str, Any]) -> None:
        '''Move a job whose run is over to the state it ended in.'''
        job_id = job["id"]
        if job["state"] == "cancelling":
            self.move(job_id, ("cancelling",), "cancelled", reason=self._reason(job_id))
        elif progress.get("state") in ("completed", "failed"):
            times = {name: progress[name] for name in ("started_at", "finished_at")
                     if progress.get(name)}
            failed = progress["state"] == "failed" or self.store.one(
                "SELECT 1 FROM job_nodes WHERE job_id = ? AND state = 'failed'", (job_id,))
            if failed:
                error = problem("run-failed", detail=progress.get("error") or "a node failed")
                self.move(job_id, ("queued", "running"), "failed",
                          error=json.dumps(error), **times)
            else:
                self.move(job_id, ("queued", "running"), "completed", **times)
        else:
            self.move(job_id, ("queued", "running"), "failed", error=json.dumps(problem(
                "run-interrupted", detail="the run ended without finishing")))

    def _sync_nodes(self, job_id: str, nodes: Dict[str, Dict[str, Any]]) -> None:
        for name, node in nodes.items():
            step, _, index = name.partition("/")
            self.store.execute(
                "UPDATE job_nodes SET state = ?, started_at = ?, finished_at = ?, "
                "exit_code = ? WHERE job_id = ? AND step = ? AND idx = ? "
                f"AND state NOT IN ({_marks(NODE_TERMINAL)})",
                (node.get("state"), node.get("started_at"), node.get("finished_at"),
                 node.get("exit_code"), job_id, step, index, *NODE_TERMINAL))

    def _reason(self, job_id: str) -> Optional[str]:
        row = self.store.one("SELECT reason FROM job_transitions WHERE job_id = ? "
                             "AND state = 'cancelling'", (job_id,))
        return row["reason"] if row else None

    def _node_names(self, job_id: str) -> List[str]:
        '''What SiliconCompiler's Slurm scheduler calls each node's job.'''
        rows = self.store.all("SELECT step, idx FROM job_nodes WHERE job_id = ?", (job_id,))
        return [SlurmSchedulerNode.get_job_name(job_id, row["step"], row["idx"]) for row in rows]

    def current(self, session, job_id: str):
        '''The caller's job, row as of now.'''
        self.reconcile(self.owned(session, job_id))
        return self.row(job_id)

    def get(self, session, job_id: str) -> Dict[str, Any]:
        return self.wire(self.current(session, job_id))

    def node_state(self, job_id: str, step: str, index: str) -> Optional[str]:
        '''A node's state as of now, which a live log waits on.'''
        self.reconcile(self.row(job_id))
        row = self.store.one("SELECT state FROM job_nodes WHERE job_id = ? AND step = ? "
                             "AND idx = ?", (job_id, step, index))
        return row["state"] if row else None

    def artifact(self, session, job_id: str, artifact_id: str):
        '''One of the caller's artifacts, as its row.'''
        job = self.owned(session, job_id)
        row = None if job["deleted_at"] else self.store.one(
            "SELECT * FROM artifacts WHERE id = ? AND job_id = ?", (artifact_id, job_id))
        if row is None:
            raise ProblemError("not-found", detail="no such artifact")
        return row

    @staticmethod
    def _limit(args) -> int:
        try:
            return max(1, min(int(args.get("limit", 50)), 200))
        except ValueError:
            raise ProblemError("invalid-request", detail="limit is a number") from None

    def artifacts(self, session, job_id: str, args) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        '''A job's artifacts, filtered by kind, step and index, over a cursor on the row order.'''
        job = self.current(session, job_id)
        if job["deleted_at"]:
            raise ProblemError("not-found", detail="no such job")

        where, params = ["job_id = ?"], [job_id]
        for name, column in (("kind", "kind"), ("step", "step"), ("index", "idx")):
            if args.getlist(name):
                where.append(f"{column} IN ({_marks(args.getlist(name))})")
                params += args.getlist(name)
        try:
            where.append("rowid > ?")
            params.append(int(args.get("cursor", 0)))
        except ValueError:
            raise ProblemError("invalid-cursor") from None

        limit = self._limit(args)
        rows = self.store.all(
            f"SELECT rowid AS position, * FROM artifacts WHERE {' AND '.join(where)} "
            "ORDER BY rowid LIMIT ?", (*params, limit + 1))
        cursor = str(rows[limit - 1]["position"]) if len(rows) > limit else None
        return [artifacts.wire(row) for row in rows[:limit]], cursor

    def listing(self, session, args) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        '''The caller's jobs, newest first, over a keyset cursor on ``(created_at, id)``.'''
        where, params = ["user_id = ?", "deleted_at IS NULL"], [session.user_id]
        for name in ("state", "design", "jobname"):
            if args.getlist(name):
                where.append(f"{name} IN ({_marks(args.getlist(name))})")
                params += args.getlist(name)
        if args.get("terminal") in ("true", "false"):
            where.append(f"state {'' if args['terminal'] == 'true' else 'NOT '}"
                         f"IN ({_marks(TERMINAL)})")
            params += TERMINAL

        if args.get("cursor"):
            try:
                created, _, last = base64.urlsafe_b64decode(
                    args["cursor"] + "=" * (-len(args["cursor"]) % 4)).decode().partition("|")
                where.append("(created_at < ? OR (created_at = ? AND id < ?))")
                params += [float(created), float(created), last]
            except ValueError:
                raise ProblemError("invalid-cursor") from None

        limit = self._limit(args)
        rows = self.store.all(f"SELECT * FROM jobs WHERE {' AND '.join(where)} "
                              "ORDER BY created_at DESC, id DESC LIMIT ?", (*params, limit + 1))
        more, rows = len(rows) > limit, rows[:limit]

        for job in rows:
            self.reconcile(job)
        cursor = None
        if more:
            cursor = base64.urlsafe_b64encode(
                f"{rows[-1]['created_at']!r}|{rows[-1]['id']}".encode()).decode().rstrip("=")
        return [self.wire(self.row(job["id"]), nodes=False) for job in rows], cursor

    def cancel(self, session, job_id: str, reason: Optional[str]) -> Dict[str, Any]:
        '''Idempotent. A job not yet submitted is `cancelled` at once; one with work
        in flight is `cancelling` until the work stops, which reconcile sees.'''
        self.owned(session, job_id)
        if reason is not None and (not isinstance(reason, str) or len(reason) > MAX_REASON
                                   or _CONTROL.search(reason)):
            raise ProblemError("invalid-request", detail=f"reason is one line of at most "
                               f"{MAX_REASON} characters")

        if self.move(job_id, ("created",), "cancelled", reason=reason):
            self.storage.discard(job_id)
        elif self.move(job_id, ("staging", "queued", "running"), "cancelling", reason=reason):
            scheduler_id = self.row(job_id)["scheduler_job_id"]
            if scheduler_id:
                self.dispatcher.cancel(scheduler_id, self._node_names(job_id))
        return self.wire(self.row(job_id))

    def delete(self, session, job_id: str) -> None:
        job = self.owned(session, job_id)
        if job["deleted_at"]:
            return
        if job["state"] not in TERMINAL:
            raise ProblemError("job-state-conflict",
                               detail="cancel this job, or let it finish, before deleting it")

        shutil.rmtree(self.root(job["user_id"], job_id), ignore_errors=True)
        shutil.rmtree(self.storage.artifact_dir(job_id), ignore_errors=True)
        self.store.execute("UPDATE jobs SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                           (time.time(), job_id))

    def wire(self, job, nodes: bool = True) -> Dict[str, Any]:
        user = self.store.one("SELECT display_name FROM users WHERE id = ?", (job["user_id"],))
        rows = self.store.all("SELECT * FROM job_nodes WHERE job_id = ? ORDER BY step, idx",
                              (job["id"],))
        count = [sum(row["state"] == state for row in rows) for state in NODE_TERMINAL]

        def when(value):
            return iso(value) if value is not None else None

        def node(row):
            failed = row["state"] == "failed"
            code = row["exit_code"]
            return {"step": row["step"], "index": row["idx"], "state": row["state"],
                    "terminal": row["state"] in NODE_TERMINAL,
                    "started_at": when(row["started_at"]),
                    "finished_at": when(row["finished_at"]), "exit_code": code,
                    "error": problem("run-failed", detail=None if code is None
                                     else f"exited with code {code}") if failed else None}

        body = {
            "id": job["id"], "state": job["state"], "terminal": job["state"] in TERMINAL,
            "transitions": [
                {"state": row["state"], "at": iso(row["at"]),
                 **({"reason": row["reason"]} if row["reason"] else {})}
                for row in self.store.all(
                    "SELECT * FROM job_transitions WHERE job_id = ? ORDER BY rowid",
                    (job["id"],))],
            "design": job["design"], "jobname": job["jobname"], "flow": job["flow"],
            "owner": {"id": job["user_id"], "name": user["display_name"]},
            "project": None, "created_at": iso(job["created_at"]),
            "submitted_at": when(job["submitted_at"]), "started_at": when(job["started_at"]),
            "finished_at": when(job["finished_at"]), "archived_at": None,
            "deleted_at": when(job["deleted_at"]),
            "deleted_reason": "deleted by its owner" if job["deleted_at"] else None,
            "error": json.loads(job["error"]) if job["error"] else None,
            "progress": {"total_count": len(rows),
                         **dict(zip(("completed_count", "failed_count", "skipped_count",
                                     "cancelled_count"), count))},
        }
        if nodes:
            body["nodes"] = [node(row) for row in rows]
        return body
