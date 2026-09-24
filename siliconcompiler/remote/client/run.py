'''
Running a design somewhere else.

Four calls to start it and one to watch it:

    POST /v1/jobs                     the job exists, and can be refused here
    POST /v1/jobs/{id}/upload-grant   where to put the bytes
    PUT  <the grant's url>            the bytes move, never through the API
    POST /v1/jobs/{id}/submit         carrying the digest of what was PUT
    GET  /v1/jobs/{id}                until `terminal`

🔴 **The refusal comes before the bytes.** That is what the descriptor on the
create body is for, and it is why the archive is built before the job is created
-- the size is the one descriptor field that costs the whole upload when it is
omitted.
'''

import hashlib
import logging
import os
import sys
import shutil
import tarfile
import tempfile
import threading
import time
import uuid

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from siliconcompiler import __version__ as sc_version
from siliconcompiler._common import NodeStatus as SCNodeStatus
from siliconcompiler.package import PythonPathResolver, FileResolver, KeyPathResolver
from siliconcompiler.schema import Parameter
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.logging import SCBlankLoggerFormatter
from siliconcompiler.utils.paths import collectiondir, jobdir

from siliconcompiler.remote.client.errors import (
    NO_NODE_FAILED, RemoteError, ServerProblem, describe)
from siliconcompiler.remote.client.results import Results
from siliconcompiler.remote.units import size as _size

__all__ = ["RemoteRun", "REMOTE_MANIFEST"]


logger = logging.getLogger(__name__)


# What a reconnect reads. Written beside the job's own manifest, because the two
# commands a user needs after a Ctrl-C both take a path rather than an id.
REMOTE_MANIFEST = "sc_remote.pkg.json"

# How long to wait when the server names no interval. Only ever a fallback: the
# server sets the pace with `Retry-After`, which is the field that replaced the
# client reading one number at the start of a run and using it to the end.
DEFAULT_POLL_SECONDS = 5

# A server error is transient and a refusal is not, so the loop keeps going
# through the first kind -- but not for ever.
MAX_TRANSIENT_POLLS = 20

# One line of node names, and the count is in the label. A thousand-node flow
# is the case this exists for.
MAX_LINE = 70


# The contract's eight node states, as SiliconCompiler's seven. An unrecognised
# state is NOT an error: the rule is read `terminal` and do not switch on the
# name, which is what made `preparing` an additive change rather than a breaking
# one.
_NODE_STATES = {
    "pending": SCNodeStatus.PENDING,
    "queued": SCNodeStatus.QUEUED,
    # Dispatched and fetching what it runs in. Waiting rather than running, so
    # a node pulling a tool image for six minutes does not read as a hang.
    "preparing": SCNodeStatus.QUEUED,
    "running": SCNodeStatus.RUNNING,
    "completed": SCNodeStatus.SUCCESS,
    "failed": SCNodeStatus.ERROR,
    "skipped": SCNodeStatus.SKIPPED,
    # The job ended before this node started. SiliconCompiler has no state for
    # it, and `error` is the honest one of the two it has: the node did not run
    # and never will.
    "cancelled": SCNodeStatus.ERROR,
}


def node_status(state: str, terminal: bool) -> str:
    '''One published node state as a SiliconCompiler status.'''
    known = _NODE_STATES.get(state)
    if known is not None:
        return known
    return SCNodeStatus.ERROR if terminal else SCNodeStatus.PENDING


class RemoteRun:
    '''One project, run on one server.'''

    def __init__(self, project, client):
        self.project = project
        self.client = client
        self.logger = project.logger.getChild("remote")

        # Everything this run prints goes through here. The tails run on their
        # own threads and the poll loop on this one, and they share a console
        # whose formatter gets swapped per line -- so they have to take turns.
        self.output_lock = threading.Lock()

    ######################################################################

    def run(self) -> None:
        if self.project.get('arg', 'step') or self.project.get('arg', 'index'):
            raise RemoteError(
                "a remote run cannot be narrowed with [arg,step] or [arg,index]: "
                "the whole flow is submitted as one job")

        # 🔴 Before anything is collected or packed. A missing server address is
        # the ordinary case now that there is no default one, and finding out
        # after a gigabyte has been tarred up is the wrong end of the run.
        self.client.transport

        resume = (not self.project.option.get_clean()
                  and self.project.get('record', 'remoteid'))

        if resume:
            job_id = self.project.get('record', 'remoteid')
            self.logger.info(f"Reconnecting to job {job_id}")
        else:
            job_id = self._start()

        self._watch(job_id)

    ######################################################################
    # Starting
    ######################################################################

    def _start(self) -> str:
        self._preprocess()

        design = self.project.name
        jobname = self.project.option.get_jobname()

        with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
            upload = Path(tmpdir) / "upload.tar.gz"
            digest, size = self._pack(upload)

            job = self.client.create_job(
                design=design, jobname=jobname,
                flow=self._flow_descriptor(),
                resources={"upload_bytes": size},
                versions={"siliconcompiler": _framework_requirement()},
                idempotency_key=_key())

            job_id = job["id"]
            self.project.set('record', 'remoteid', job_id)

            if job["state"] in ("completed", "failed"):
                # A job this server already has. Nothing was uploaded and
                # nothing will run; the results are whatever it kept.
                self.logger.info(f"Server returned an existing job: {job_id}")
                return job_id

            self.logger.info(f"Your job's reference ID is: {job_id}")

            # 🔴 Followed, never constructed. The portal's route shape may
            # change without a version bump, so this is printed only when the
            # server sent it -- absent means the deployment has no web UI,
            # which is a real answer rather than a missing one. It is also the
            # whole reason the member exists: an id is useless to paste into a
            # browser.
            if job.get("web_url"):
                self.logger.info(f"Watch it at: {job['web_url']}")
                self._open_portal(job_id)

            self._save_manifest()

            grant = self.client.upload_grant(job_id)
            self.logger.info(f"Uploading {_size(size)}")
            self.client.upload(grant, upload)

            self.client.submit_job(job_id, digest=digest, size=size,
                                   idempotency_key=_key())

        self.logger.info("Job submitted")
        return job_id

    def _open_portal(self, job_id: str) -> None:
        '''Open the job's page, where a person is plainly watching.

        ⚠️ **Provisional.** Launching a browser from a build is a convenience
        and not a commitment: the durable part is `web_url` on the job object,
        which is printed either way. If this proves more annoying than useful,
        deleting this method and its one call site removes it entirely and
        changes nothing else.

        🔴 A browser is opened only when somebody is there to see it. Three
        things have to agree:

        - the server published a `web_url`, so there IS a portal
        - `option,nodisplay` is not set, which is SiliconCompiler's existing
          way of saying *do not pop anything up* and is already honoured by the
          dashboard and the layout viewers
        - stdout is a terminal, which is the cheap proxy for *a person ran
          this*. A CI job that opened a browser on a build agent would be a
          small mystery at best

        ⚠️ `open_portal` in the credentials file overrides all of it either
        way, because a proxy is a guess and somebody will want it wrong on
        purpose.

        A handover rather than the bare URL: the browser holds none of what
        this client holds, so the plain page would answer 401 and ask them to
        run a command. This mints a single-use link that both authenticates
        and lands on the job.
        '''
        wanted = self.client.credentials.get("open_portal")
        if wanted is False:
            return
        if not wanted:
            if self.project.option.get_nodisplay():
                return
            if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
                return

        try:
            self.client.portal(open_browser=True,
                               landing=f"/portal/jobs/{job_id}")
        except Exception as e:                                   # noqa: BLE001
            # A browser that will not open is not a reason to stop a run, and
            # the URL has already been printed.
            logger.debug(f"could not open the portal: {e}")

    def _preprocess(self) -> None:
        '''Collect everything the server will need, because it has none of it.

        A dataroot resolved from an installed Python package, a local path or
        another schema key exists only on this machine, so anything reached
        through one is marked for copying before the collection runs.
        '''
        for key in self.project.allkeys():
            if key[0] == "history":
                continue

            param: Parameter = self.project.get(*key, field=None)
            if not param.is_path:
                continue

            schema_obj = self.project.get(*key[:-1], field="schema")
            resolvers = schema_obj._find_files_dataroot_resolvers(True)

            for value, step, index in param.getvalues():
                if not value:
                    continue
                dataroots = param.get(field='dataroot', step=step, index=index)
                if not isinstance(dataroots, list):
                    dataroots = [dataroots]
                for dataroot in dataroots:
                    if not dataroot:
                        continue
                    if isinstance(resolvers.get(dataroot),
                                  (PythonPathResolver, FileResolver, KeyPathResolver)):
                        self.project.set(*key, True, field='copy', step=step, index=index)
                        break

        collect(self.project,
                whitelist=list(self.client.credentials.directory_whitelist))

    def _pack(self, upload: Path) -> Tuple[str, int]:
        '''The job directory, as one archive, with its manifest inside it.

        The manifest goes in rather than beside: the server re-derives every
        advisory value from it, and a manifest sent as a separate field would be
        a second copy of the truth arriving on a different path from the bytes
        it describes.
        '''
        root = jobdir(self.project)
        self.project.write_manifest(
            os.path.join(root, f"{self.project.name}.pkg.json"))

        with tarfile.open(upload, mode="w:gz") as tar:
            tar.add(root, arcname="")

        collected = collectiondir(self.project)
        if collected and os.path.isdir(collected):
            # It is in the archive now, and it is the largest thing in the build
            # directory. Keeping a second copy on this machine is what the old
            # client did and nobody asked for.
            shutil.rmtree(collected, ignore_errors=True)

        digest = hashlib.sha256()
        size = 0
        with open(upload, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)

        return f"sha256:{digest.hexdigest()}", size

    def _flow_descriptor(self) -> Optional[Dict[str, Any]]:
        '''What the server can refuse us on before the upload moves.

        Advisory, re-derived at submit, and refusing to build it is never worth
        failing the run over -- a sparse descriptor is legal and costs only the
        check it would have answered.
        '''
        try:
            from siliconcompiler.remote.server.runspec import runtime_nodes

            flow = self.project.get_flow()
            return {"name": flow.name, "nodes": len(runtime_nodes(self.project))}
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"no flow descriptor: {e}")
            return None

    def _save_manifest(self) -> None:
        path = os.path.join(jobdir(self.project), REMOTE_MANIFEST)
        self.project.write_manifest(path)

    ######################################################################
    # Watching
    ######################################################################

    def reconnect(self, job_id: Optional[str] = None) -> None:
        '''Re-enter the wait for a job that is already running.

        🔴 This is the answer to Ctrl-C, and the only way back to a detached
        job. A long run that a user interrupted must not be a run they have lost
        -- which is why the job id goes into the manifest before the upload
        rather than after the submit.
        '''
        job_id = job_id or self.project.get('record', 'remoteid')
        if not job_id:
            raise RemoteError(
                "this manifest names no remote job: it was never submitted, "
                "or it was submitted by a different run")
        self._watch(job_id)

    def _watch(self, job_id: str) -> None:
        try:
            self._poll(job_id)
        except KeyboardInterrupt:
            manifest = os.path.join(jobdir(self.project), REMOTE_MANIFEST)
            self.logger.info("Disconnecting from remote job")
            self.logger.info(f"To reconnect to this job use: sc-remote -cfg {manifest} -reconnect")
            self.logger.info(f"To cancel this job use: sc-remote -cfg {manifest} -cancel")
            raise

    def _poll(self, job_id: str) -> None:
        transient = 0
        seen: Dict[Tuple[str, str], str] = {}
        tails = _Tails(self)
        results = Results(self.project, self.client)

        while True:
            try:
                job, retry_after = self.client.job(job_id)
                transient = 0
            except ServerProblem as refusal:
                if _is_refusal(refusal):
                    # 🔴 A refusal ends the wait AS A FAILURE. Falling through
                    # would announce a finished job with nothing in it, which is
                    # the opposite of what happened.
                    self.logger.error(str(refusal))
                    raise RemoteError(
                        f"the server will not report on job {job_id}") from None

                transient += 1
                if transient > MAX_TRANSIENT_POLLS:
                    raise RemoteError(
                        f"the server has been failing for {transient} polls; "
                        f"job {job_id} may still be running") from None
                self.logger.warning(str(refusal))
                time.sleep(DEFAULT_POLL_SECONDS)
                continue

            changed = self._record(job, seen)
            results.take(job_id, job)
            self._paint(job)
            tails.follow(job_id, job)

            if job.get("terminal"):
                break

            self._report(job, changed)
            time.sleep(retry_after or DEFAULT_POLL_SECONDS)

        tails.finish()
        self._finish(job, results)

    def _record(self, job: Dict[str, Any], seen) -> list:
        '''Write what the server says into this project's record.

        Returns the nodes whose state moved since the last poll, which is all
        the output a dashboard run needs: the dashboard is already showing
        every node's state, so repeating the whole table each poll is noise
        over the top of it.

        Tolerant on purpose: a body that is not the documented shape must not
        end a run that is still going. What cannot be read is skipped, and the
        loop is driven by `terminal` alone.
        '''
        changed = []

        for node in job.get("nodes") or []:
            step, index = node.get("step"), node.get("index")
            if not step or index is None:
                continue
            status = node_status(node.get("state"), node.get("terminal", False))
            try:
                self.project.set('record', 'status', status, step=step, index=index)
            except Exception as e:                               # noqa: BLE001
                logger.debug(f"could not record {step}/{index}: {e}")
                continue

            if seen.get((step, index)) != status:
                changed.append((step, index, node.get("state")))
            seen[(step, index)] = status

        return changed

    def _report(self, job: Dict[str, Any], changed=None) -> None:
        with self.output_lock:
            self._report_locked(job, changed)

    def _report_locked(self, job: Dict[str, Any], changed=None) -> None:
        if self._dashboard():
            # 🔴 The dashboard is already rendering every node's state, so the
            # full table underneath it is the same information twice. What it
            # cannot show is the moment something moved.
            for step, index, state in changed or []:
                self.logger.info(f"  {step}/{index} -> {state}")
            return

        by_state: Dict[str, list] = {}
        for node in job.get("nodes") or []:
            by_state.setdefault(node.get("state", "unknown"), []).append(node)

        progress = job.get("progress") or {}
        self.logger.info(
            f"Job is still running ({job.get('state')}): "
            f"{progress.get('completed_count', 0)}/{progress.get('total_count', 0)} nodes")

        for state in sorted(by_state):
            self._report_state(state, by_state[state])

    def _report_state(self, state: str, nodes: list) -> None:
        '''One line per state, truncated, with the count in the label.'''
        names = []
        length = 0
        for node in nodes:
            name = f"{node.get('step')}/{node.get('index')}"
            if length + len(name) + 2 < MAX_LINE:
                names.append(name)
                length += len(name) + 2
            else:
                names.append("...")
                break
        self.logger.info(f"  {state.title()} ({len(nodes)}): {', '.join(names)}")

    def _paint(self, job: Dict[str, Any]) -> None:
        '''Hand the dashboard the states and the clocks.

        🔴 Without this the dashboard renders whatever it had when the run
        started: the record is updated on this project, and nothing tells the
        board to look at it again.

        ``starttimes`` is what makes the per-node timer run. The client this
        replaces had to derive it -- the old server sent an elapsed string like
        ``0:01:05`` and the client subtracted it from now, which restarted the
        clock at every poll and drifted. `v1` publishes ``started_at`` as an
        instant, so a node's timer is continuous across a poll, across a
        reconnect, and across a client restart.
        '''
        board = self._dashboard()
        if board is None:
            return

        try:
            board.update_manifest({"starttimes": _starttimes(job)})
        except Exception as e:                                   # noqa: BLE001
            # A repaint that fails is a repaint. It must not end a run.
            logger.debug(f"could not update the dashboard: {e}")

    def _dashboard(self):
        '''The dashboard this run is being watched through, if any.'''
        board = getattr(self.project, "_Project__dashboard", None)
        try:
            return board if board is not None and board.is_running() else None
        except Exception:                                        # noqa: BLE001
            return None

    def _finish(self, job: Dict[str, Any], results=None) -> None:
        state = job.get("state")

        if state == "completed":
            self.logger.info("Remote job completed")
        elif job.get("error"):
            self.logger.error(f"Remote job {state}: {_why_it_failed(job)}")
        else:
            self.logger.error(f"Remote job {state}")

        # 🔴 Retrieved on EVERY terminal state, not only on success. A failed
        # run is the one whose log and manifest a user most wants, and a client
        # that fetches nothing when a job fails has hidden the evidence at the
        # moment it became useful.
        try:
            (results or Results(self.project, self.client)).fetch(job["id"])
        except ServerProblem as e:
            self.logger.error(str(e))
        except RemoteError as e:
            self.logger.error(f"Could not retrieve results: {e}")

        # Unset so that a later summary() or show() is not narrowed by a run
        # that is over.
        self.project.option.unset('remote')

        if state != "completed":
            raise RemoteError(f"the remote job ended {state}")


class _Tails:
    '''The live logs of whatever is running, on this terminal.

    🔴 One stream per running node, interleaved. SiliconCompiler's own log
    lines already carry ``job | step | index``, so several at once read exactly
    the way a local run does -- which is the point: a remote run should not
    look like a different program.

    Bounded by the server's published ``concurrent_log_streams``, because it is
    the server's thread and file descriptor being held. Nodes past the ceiling
    are named once and their logs arrive with the results like everything else.
    '''

    def __init__(self, run: "RemoteRun"):
        self._run = run
        self._client = run.client
        self._logger = run.logger

        self._threads: Dict[Tuple[str, str], threading.Thread] = {}
        self._started: set = set()
        self._over_ceiling: set = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self._enabled, self._ceiling = self._decide()

    def _decide(self) -> Tuple[bool, int]:
        '''Whether to tail at all, and how many at once.

        Three things can switch it off, and only one of them is an opinion:
        the deployment does not serve a live tail, or the caller asked for
        quiet -- which means the same thing here as it does locally, *do not
        put tool output on my terminal*.
        '''
        if self._run.project.option.get_quiet():
            return False, 0

        try:
            capabilities = self._client.capabilities()
        except RemoteError as e:
            logger.debug(f"no capabilities, so no tailing: {e}")
            return False, 0

        if "logs.stream" not in (capabilities.get("features") or []):
            # 🔴 Absent and unrecognised mean the same thing. The archived log
            # still arrives with the results, so this costs the live view and
            # not the log.
            return False, 0

        ceiling = (capabilities.get("limits") or {}).get("concurrent_log_streams")
        return True, max(1, int(ceiling or 1))

    def follow(self, job_id: str, job: Dict[str, Any]) -> None:
        '''Start a tail for anything newly running.'''
        if not self._enabled:
            return

        for node in job.get("nodes") or []:
            if node.get("state") != "running":
                continue

            key = (node.get("step"), node.get("index"))
            if None in key or key in self._started:
                continue

            if len(self._threads) >= self._ceiling:
                if key not in self._over_ceiling:
                    self._over_ceiling.add(key)
                    self._logger.info(
                        f"  (not tailing {key[0]}/{key[1]}: this server allows "
                        f"{self._ceiling} live logs at once)")
                continue

            self._started.add(key)
            thread = threading.Thread(
                target=self._tail, args=(job_id, *key), daemon=True)
            self._threads[key] = thread
            thread.start()

    def _tail(self, job_id: str, step: str, index: str) -> None:
        try:
            self._client.tail_log(job_id, step, index, write=self._write)
        except Exception as e:                                   # noqa: BLE001
            # One node's log going away must not disturb the run or the other
            # tails. It is still fetched with the results.
            logger.debug(f"stopped tailing {step}/{index}: {e}")
        finally:
            with self._lock:
                self._threads.pop((step, index), None)

    def _write(self, text: str) -> None:
        '''One chunk of somebody's log, on the one terminal everybody shares.

        🔴 Emitted with a blank formatter, because these lines are already
        formatted: they come out of a node's own log, which carries
        ``job | step | index`` on every line. Logging them normally produced
        ``| INFO | job0 | remote | - | | INFO | job0 | route.detailed | 0 | …``
        -- this run's prefix stamped on top of the prefix that says which node
        it actually came from.

        Swapping the CONSOLE handler's formatter covers the dashboard too: its
        sink formats with whatever the terminal handler currently has, so one
        swap serves both and there is no branch on which is listening. It is
        the same thing the Slurm scheduler does when it echoes a node's log.
        '''
        if self._stop.is_set():
            return

        console = getattr(self._run.project, "_logger_console", None)

        with self._run.output_lock:
            original = console.formatter if console is not None else None
            if console is not None:
                console.setFormatter(SCBlankLoggerFormatter())
            try:
                for line in text.splitlines():
                    self._logger.info(line)
            finally:
                if console is not None:
                    console.setFormatter(original)

    def finish(self, timeout: float = 5.0) -> None:
        '''Let the tails drain, then stop waiting for them.

        A tail normally ends itself when its node does. This bounds the case
        where one is mid-reconnect as the job goes terminal: the log is in the
        results either way, so waiting on it is a courtesy rather than a
        requirement.
        '''
        for thread in list(self._threads.values()):
            thread.join(timeout=timeout)
        self._stop.set()


def _starttimes(job: Dict[str, Any]) -> Dict[Tuple[str, str], float]:
    '''When each node started, in the shape the dashboard already takes.

    Keyed by (step, index) and valued in epoch seconds, which is what a local
    run hands it.
    '''
    starttimes = {}

    for node in job.get("nodes") or []:
        step, index = node.get("step"), node.get("index")
        started = node.get("started_at")
        if not step or index is None or not started:
            continue

        if node.get("terminal"):
            # 🔴 A finished node must stop counting. `starttimes` is what the
            # board ticks against `now`, so leaving one here would have a node
            # that ended ten minutes ago still climbing. The board renders a
            # done node from `metric,tasktime` instead -- which arrives when
            # that node's manifest is replayed, out of the archive fetched as it
            # finished.
            continue

        moment = _epoch(started)
        if moment is not None:
            starttimes[(step, index)] = moment

    return starttimes


def _epoch(timestamp: str) -> Optional[float]:
    '''An RFC 3339 instant as epoch seconds, or None if it cannot be read.

    Unreadable is not fatal: it costs one node its timer, where raising would
    cost the run.
    '''
    from datetime import datetime, timezone

    try:
        moment = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        logger.debug(f"unreadable timestamp: {timestamp!r}")
        return None

    if moment.tzinfo is None:
        # The contract says UTC; a server that omits the offset meant it.
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _why_it_failed(job: Dict[str, Any]) -> str:
    '''Three lines about the failure, without opening a URL.

    The `type` pages are static and identical on every deployment, so the server
    cannot say anything specific through them -- which leaves the client holding
    the only copy of the specific failure.

    🔴 The advice is chosen from the job and not from the slug alone. A run can
    fail with no failed node at all -- it died before the first one, or in
    setup, and every node reads `cancelled` -- and *read the failing node's
    log* then names a file nobody can open.
    '''
    error = job.get("error") or {}
    if not error.get("type"):
        return "no reason given"

    # Only `run-failed` -- it is the one whose advice names a node. Every other
    # slug's advice is about the job and stays right however the nodes ended:
    # `scheduler-lost` says submit it again, and it would be no less true for a
    # run that got halfway.
    failed = (job.get("progress") or {}).get("failed_count")
    ran_out = str(error["type"]).rstrip("/").rsplit("/", 1)[-1] == "run-failed"

    return describe(error,
                    next_step=NO_NODE_FAILED if ran_out and failed == 0 else None)


def _is_refusal(problem: ServerProblem) -> bool:
    '''Whether to stop polling.

    🔴 The discriminator is the `type` slug and never the status alone. A 5xx
    with no slug is a server having a bad minute; a named condition is an answer
    that will not change by asking again.
    '''
    if problem.slug is None:
        return False
    return problem.slug not in ("not-ready", "rate-limited")


def _framework_requirement() -> str:
    """What this client needs the server's framework image to hold.

    The request carries a PEP 440 specifier and the SERVER resolves it, which
    is what lets a deployment answer *which image has all of these* -- a
    question a client cannot answer, because `GET /v1`'s `software` map is flat
    per name while the image join is over combinations.

    🔴 **`==` and deliberately not `>=`, which is the tempting one.** Reading a
    manifest is only backwards compatible: a newer SiliconCompiler reads an
    older manifest, and the reverse either fails or quietly returns something
    other than what was written. `>=` gets the upload read correctly -- a newer
    image reads this client's manifest -- and then every manifest that comes
    BACK is written by that newer version and read by this one, which is the
    unsupported direction. The node states and the metrics `summary()` prints
    come out of those.

    ⚠️ So the ceiling is not caution, it is the same rule in the other
    direction. A deployment that wants a range here is asking this client to
    read manifests it cannot.
    """
    return f"=={sc_version}"


def _key() -> str:
    return str(uuid.uuid4())
