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
import shutil
import tarfile
import tempfile
import time
import uuid

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from siliconcompiler import __version__ as sc_version
from siliconcompiler._common import NodeStatus as SCNodeStatus
from siliconcompiler.package import PythonPathResolver, FileResolver, KeyPathResolver
from siliconcompiler.schema import Parameter
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.paths import collectiondir, jobdir

from siliconcompiler.remote.client.errors import RemoteError, ServerProblem

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
                versions={"siliconcompiler": sc_version},
                idempotency_key=_key())

            job_id = job["id"]
            self.project.set('record', 'remoteid', job_id)

            if job["state"] in ("completed", "failed"):
                # A job this server already has. Nothing was uploaded and
                # nothing will run; the results are whatever it kept.
                self.logger.info(f"Server returned an existing job: {job_id}")
                return job_id

            self.logger.info(f"Your job's reference ID is: {job_id}")
            self._save_manifest()

            grant = self.client.upload_grant(job_id)
            self.logger.info(f"Uploading {size} bytes")
            self.client.upload(grant, upload)

            self.client.submit_job(job_id, digest=digest, size=size,
                                   idempotency_key=_key())

        self.logger.info("Job submitted")
        return job_id

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

            self._record(job, seen)

            if job.get("terminal"):
                break

            self._report(job)
            time.sleep(retry_after or DEFAULT_POLL_SECONDS)

        self._finish(job)

    def _record(self, job: Dict[str, Any], seen) -> None:
        '''Write what the server says into this project's record.

        Tolerant on purpose: a body that is not the documented shape must not
        end a run that is still going. What cannot be read is skipped, and the
        loop is driven by `terminal` alone.
        '''
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
            seen[(step, index)] = status

    def _report(self, job: Dict[str, Any]) -> None:
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

    def _finish(self, job: Dict[str, Any]) -> None:
        state = job.get("state")

        if state == "completed":
            self.logger.info("Remote job completed")
        elif job.get("error"):
            self.logger.error(f"Remote job {state}: {job['error'].get('title')}")
        else:
            self.logger.error(f"Remote job {state}")

        # Fetching what the run produced is the next endpoint group and is not
        # on this branch yet, so say so rather than leaving a user looking at an
        # empty build directory and guessing.
        self.logger.info(
            "Results are on the server. Retrieving them is not available yet: "
            "the artifact endpoints land in the next phase.")

        # Unset so that a later summary() or show() is not narrowed by a run
        # that is over.
        self.project.option.unset('remote')

        if state != "completed":
            raise RemoteError(f"the remote job ended {state}")


def _is_refusal(problem: ServerProblem) -> bool:
    '''Whether to stop polling.

    🔴 The discriminator is the `type` slug and never the status alone. A 5xx
    with no slug is a server having a bad minute; a named condition is an answer
    that will not change by asking again.
    '''
    if problem.slug is None:
        return False
    return problem.slug not in ("not-ready", "rate-limited")


def _key() -> str:
    return str(uuid.uuid4())
