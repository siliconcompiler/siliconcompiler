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
import re
import sys
import shutil
import tarfile
import tempfile
import threading
import time
import uuid

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler import __version__ as sc_version
from siliconcompiler._common import NodeStatus as SCNodeStatus
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.logging import SCBlankLoggerFormatter
from siliconcompiler.utils.paths import collectiondir, jobdir, workdir

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

        # What went into the last archive, per dataroot, and the requests for
        # sources already answered -- so a server asking again for the same
        # ones is a failure, not a loop.
        self._uploading = []
        self._sent = set()

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

        from siliconcompiler.remote import owners

        with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
            upload = Path(tmpdir) / "upload.tar.gz"
            digest, size = self._pack(upload)

            job = self.client.create_job(
                design=design, jobname=jobname,
                flow=self._flow_descriptor(),
                resources={"upload_bytes": size},
                versions={"python": {"siliconcompiler": sc_version},
                          "tools": {}},
                requires={"python": {"siliconcompiler": _framework_requirement()},
                          "tools": self._tool_requirements()},
                # What this machine expects the server to supply. A lookup at
                # the other end, never a fetch, and credentials stripped.
                sources=owners.sources(self.project) or None,
                idempotency_key=_key())

            asked = job.get("upload_sources") or []
            if asked:
                # 🔴 What the server cannot supply, it asks for (D114): this
                # machine resolves those with its OWN credentials and puts them
                # in the archive -- or fails here, before a byte moves.
                self.logger.info(f"The server asked for {_named(asked)}")
                self._collect(asked)
                digest, size = self._pack(upload)

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

            grant = self.client.upload_grant(job_id, size)
            self._report_upload(size)
            self.client.upload(grant, upload)

            self.client.submit_job(job_id, digest=digest, size=size,
                                   idempotency_key=_key())

        self.logger.info("Job submitted")
        return job_id

    def _needed_from(self, root: str) -> List[str]:
        '''What else of the job directory the run reads, relative to it.

        The collected sources -- whatever `collect` copied, which is the whole
        point of collecting -- and, for a run that starts part-way through the
        flow (`option,from`), the results of the nodes it starts FROM: they
        exist on this machine and nowhere else, and the first node to run reads
        their outputs as its inputs. Nothing a node this run will execute left
        behind is sent, because the run replaces it.
        '''
        from siliconcompiler.remote.server.runspec import runtime_flow

        needed = []

        collected = collectiondir(self.project)
        if collected and os.path.isdir(collected):
            needed.append(os.path.relpath(collected, root))

        try:
            runtime = runtime_flow(self.project)
            running = set(runtime.get_nodes())
            upstream = sorted({source for node in running
                               for source in runtime.get_node_inputs(*node)
                               if source not in running})
        except Exception as e:                                   # noqa: BLE001
            # A flow that will not resolve fails at the server with a reason;
            # this is only deciding what to send.
            logger.debug(f"could not tell which upstream results to send: {e}")
            upstream = []

        for step, index in upstream:
            node = workdir(self.project, step=step, index=index)
            if os.path.isdir(node):
                needed.append(os.path.relpath(node, root))

        return needed

    def _report_upload(self, size: int, report=None) -> None:
        '''What goes up, per dataroot, with sizes -- before it goes.

        🔴 Said every time, because what is uploaded is decided by rule rather
        than by the user, and a PDK uploaded by mistake is gigabytes and, for a
        proprietary one, a disclosure.
        '''
        report = self._uploading if report is None else report
        self.logger.info(f"Uploading {_size(size)}")
        for kind, name, dataroot, weight, files in report:
            where = f" ({dataroot})" if dataroot else ""
            self.logger.info(f"  {kind} {name}{where}: {_size(weight)}, "
                             f"{files} file{'s' if files != 1 else ''}")

    def _send_asked(self, job_id: str, asked) -> None:
        '''The follow-up for a job sent back to `awaiting_input` (D124): an
        archive of ONLY what the server asked for, its own grant, and submit
        again.'''
        import hashlib

        from siliconcompiler.remote import owners

        seen = tuple(sorted((item.get("kind"), item.get("name"), item.get("dataroot"))
                            for item in asked))
        if seen in self._sent:
            raise RemoteError(f"the server asked again for {_named(asked)}, which "
                              "this client has already sent")
        self._sent.add(seen)

        self.logger.info(f"The server could not fetch {_named(asked)}; sending it")
        with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
            collection = Path(tmpdir) / "sc_collected_files"
            self._collect(asked, directory=str(collection), only_asked=True)

            upload = Path(tmpdir) / "follow-up.tar.gz"
            with tarfile.open(upload, mode="w:gz") as tar:
                tar.add(str(collection), arcname="sc_collected_files")

            digest, size = hashlib.sha256(), 0
            with open(upload, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)

            grant = self.client.upload_grant(job_id, size)
            self._report_upload(size, owners.upload_report(self.project, collection))
            self.client.upload(grant, upload)
            self.client.submit_job(job_id, digest=f"sha256:{digest.hexdigest()}",
                                   size=size, idempotency_key=_key())

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
        '''Collect what the server will need and cannot have, by what owns it.

        🔴 **The design always; a PDK's, library's, FPGA device's or tool's
        files only where their source is local or editable** -- see
        `siliconcompiler.remote.owners`. **No flag is consulted, and nothing is
        advertised:** the server either holds what was left out or refuses the
        job at submit, naming it (`resource-unavailable`).

        It used to mark `copy=True` on anything reached through a local path,
        a Python package or another key, and let `collect` read the flag. Two
        things were wrong with that: a flag set by this client was written into
        the caller's own project, and "a Python package" included one installed
        normally -- the same package the server's image already has -- while
        leaving a design file with no dataroot at all behind. `copy=True` still
        drives `collect()` everywhere else, `sc-issue` included; it just does
        not decide what a remote run uploads.

        ⚠️ **Hashes are not required.** Where the caller set `option,hash` the
        manifest carries them; nothing here computes one, because hashing a PDK
        takes minutes.
        '''
        self._collect()

    def _collect(self, asked=(), directory=None, only_asked: bool = False) -> None:
        '''Collect by owner -- plus, where the server asked, those sources too.

        ``asked`` is an `upload_sources` list. A private dataroot is never
        collected, asked or not: it must not leave this machine.
        '''
        from siliconcompiler.remote import owners

        wanted = {(item.get("kind"), item.get("name"), item.get("dataroot"))
                  for item in asked}

        def select(key, dataroot, resolvers, path):
            if owners.skipped(key):
                return False
            origin = owners.source(resolvers, dataroot, path=path)
            if origin == owners.PRIVATE:
                return False
            if not only_asked and owners.uploads(self.project, key, dataroot,
                                                 resolvers, path):
                return True
            who, name = owners.owner(self.project, key)
            kind = owners.DESIGN if who == owners.PROJECT else who
            name = self.project.name if who == owners.PROJECT else name
            return (kind, name, dataroot) in wanted

        try:
            collect(self.project, directory=directory, verbose=directory is None,
                    whitelist=list(self.client.credentials.directory_whitelist),
                    select=select)
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            if not asked:
                raise
            # 🔴 The user cannot reach it either: fail here, naming it, and
            # upload nothing.
            raise RemoteError(
                f"the server asked for {_named(asked)}, and this machine cannot "
                f"reach it either: {e}") from None

    def _pack(self, upload: Path) -> Tuple[str, int]:
        '''What the server needs of the job directory, as one archive, with
        the manifest inside it.

        The manifest goes in rather than beside: the server re-derives every
        advisory value from it, and a manifest sent as a separate field would be
        a second copy of the truth arriving on a different path from the bytes
        it describes.

        🔴 **Named, not the whole directory.** It used to be `tar.add(jobdir)`,
        and a job directory that has run before holds far more than a run
        needs: the last run's `sc_remote.pkg.json`, its `remote-job.log`, the
        rotated `job.<time>.log` files, and every node directory fetched back
        from it. A four-file design uploaded three quarters of a megabyte, most
        of it the previous run's logs -- and `job.log` itself, which this very
        run has open and is appending to.
        '''
        root = jobdir(self.project)
        manifest = f"{self.project.name}.pkg.json"
        self.project.write_manifest(os.path.join(root, manifest))

        with tarfile.open(upload, mode="w:gz") as tar:
            for name in [manifest, *self._needed_from(root)]:
                tar.add(os.path.join(root, name), arcname=name)

        collected = collectiondir(self.project)
        from siliconcompiler.remote import owners
        self._uploading = owners.upload_report(self.project, collected) \
            if collected and os.path.isdir(collected) else []
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

    def _tool_requirements(self) -> Dict[str, Any]:
        """What this flow will reach for, so the server can refuse early.

        🔴 **The point is the refusal BEFORE the upload.** The server derives
        the same tool list from the manifest at submit, so this changes no
        placement -- what it changes is when a deployment that curates images
        for OpenROAD and has none says so: at create, for free, instead of
        after the whole archive has moved.

        ⚠️ **Every value is a LIST, because a version requirement is one.**
        `Task.get('version')` holds alternative specifier sets and
        `check_exe_version` accepts a match against any, so two tasks of the
        same tool contribute two entries rather than one of them winning. An
        empty list is *any version of this*, which is what a client that knows
        the tool and not the version means -- and is the ordinary case, since
        a task's requirement is set in `setup()` and setup happens in the
        image.

        ⚠️ Advisory, like the rest of the descriptor, and never worth failing
        a run over. A flow this cannot walk sends nothing and is checked at
        submit like every other sparse descriptor.
        """
        wanted: Dict[str, Any] = {}
        try:
            from siliconcompiler.remote.server.runspec import (
                node_tools, runtime_nodes)

            flow = self.project.get_flow()
            for node, tool in node_tools(flow, runtime_nodes(self.project)).items():
                if not tool:
                    continue
                for one in self._declared_versions(flow, node):
                    if one not in wanted.setdefault(tool, []):
                        wanted[tool].append(one)
                wanted.setdefault(tool, [])
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"no tool requirements: {e}")
            return {}

        return wanted

    @staticmethod
    def _declared_versions(flow, node) -> List[str]:
        """What one node's task says it needs of its tool, if it says anything.

        🔴 **Normalised with the TASK's own `normalize_version`, the same way
        `check_exe_version` does it before comparing.** OpenROAD declares
        `>=24Q3-2011`, which is not a PEP 440 specifier at all -- sent raw, the
        server cannot parse it, falls back to comparing the string, and refuses
        an image that plainly satisfies it. The driver is the only thing that
        knows how to turn that into something comparable, and the client is the
        side that has the driver.

        ⚠️ The operator is kept and only the VERSION is normalised, because
        `>=` means the same thing in both spellings and the version does not.

        ⚠️ Usually there is nothing to normalise. A task declares its version
        requirement inside `setup()`, and setup runs where the flow runs -- in
        the image, on the compute node. Reading it here would mean running
        every node's setup locally for a run whose whole point is not to run
        locally.
        """
        try:
            step, index = node
            task = flow.get_task_module(step, index)()
        except Exception:                                        # noqa: BLE001
            return []

        found = []
        for declared in task.get("version") or []:
            normalized = _normalize_spec(task, declared)
            if normalized:
                found.append(normalized)
        return found

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

            if job.get("state") == "awaiting_input" and job.get("upload_sources"):
                # Sent back: a source the server could not fetch. The job is
                # not terminal, so the wait goes on once it has been sent.
                self._send_asked(job_id, job["upload_sources"])
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
            board.update_manifest({"starttimes": _starttimes(job),
                                   "durations": _durations(job)})
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
            self.logger.error(f"Remote job {state}: "
                              f"{_why_it_failed(job, self.client.transport.help_pages)}")
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

    🔴 **One stream for the whole job where the server offers it**
    (`logs.stream.job`), and one per running node where it does not. Either way
    the lines interleave, and SiliconCompiler's own log lines already carry
    ``job | step | index``, so several at once read exactly the way a local run
    does -- which is the point: a remote run should not look like a different
    program.

    The job stream is one connection however wide the flow, so it is also the
    only way to watch every node of a flow wider than the server's
    ``concurrent_log_streams``. Per node, that ceiling bounds how many are
    followed; nodes past it are named once and their logs arrive with the
    results like everything else.
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

        # Every archived log's id, as the job stream's `node_state` events name
        # them.
        self.artifact_ids: Dict[Tuple[str, str], str] = {}

        self._enabled, self._ceiling, self._whole_job = self._decide()

    def _decide(self) -> Tuple[bool, int, bool]:
        '''Whether to tail at all, how many at once, and whether as one
        stream for the whole job.

        Three things can switch it off, and only one of them is an opinion:
        the deployment does not serve a live tail, or the caller asked for
        quiet -- which means the same thing here as it does locally, *do not
        put tool output on my terminal*.
        '''
        if self._run.project.option.get_quiet():
            return False, 0, False

        try:
            capabilities = self._client.capabilities()
        except RemoteError as e:
            logger.debug(f"no capabilities, so no tailing: {e}")
            return False, 0, False

        features = capabilities.get("features") or []
        if "logs.stream" not in features:
            # 🔴 Absent and unrecognised mean the same thing. The archived log
            # still arrives with the results, so this costs the live view and
            # not the log.
            return False, 0, False

        ceiling = (capabilities.get("limits") or {}).get("concurrent_log_streams")
        return True, max(1, int(ceiling or 1)), "logs.stream.job" in features

    def follow(self, job_id: str, job: Dict[str, Any]) -> None:
        '''Start a tail for anything newly running.'''
        if not self._enabled:
            return

        if self._whole_job:
            # One stream, opened once something is running: asked before any
            # node has started, the job form answers `not-ready`.
            if JOB not in self._started and any(
                    node.get("state") == "running" for node in job.get("nodes") or []):
                self._started.add(JOB)
                thread = threading.Thread(target=self._tail_job, args=(job_id,),
                                          daemon=True)
                self._threads[JOB] = thread
                thread.start()
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

    def _tail_job(self, job_id: str) -> None:
        from siliconcompiler.remote.client.logs import LogTail

        tail = LogTail(self._client, job_id)
        try:
            tail.follow(write=self._write)
        except ServerProblem as refusal:
            if refusal.slug == "feature-unsupported" and \
                    refusal.member("feature") == "logs.stream.job":
                # 🔴 Permanent, so the job form is never asked for again: this
                # deployment follows one node at a time, starting at the next
                # poll.
                logger.debug("no job stream here; following each node instead")
                self._whole_job = False
            elif refusal.slug == "not-ready":
                # Nothing had started by the time it was asked. Transient:
                # the next poll asks again.
                self._started.discard(JOB)
            else:
                logger.debug(f"stopped following the job's log: {refusal}")
        except Exception as e:                                   # noqa: BLE001
            # The log is still fetched with the results.
            logger.debug(f"stopped following the job's log: {e}")
        finally:
            self.artifact_ids.update(tail.artifact_ids)
            with self._lock:
                self._threads.pop(JOB, None)

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


# The key the job stream's thread is held under, beside the per-node keys it
# replaces. Not a (step, index) any flow can have.
JOB = (None, None)


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


def _durations(job: Dict[str, Any]) -> Dict[Tuple[str, str], float]:
    '''How long each finished node took, as the server saw it.

    🔴 **The job object already says when every node started and ended**, so a
    finished node's time does not have to wait for its manifest -- which comes
    a poll later, and not at all from a deployment that withholds it. The board
    shows `metric,tasktime` where it has one and this where it does not, so the
    tool's own number replaces the server's the moment it arrives.

    ⚠️ Wall time on the server, not the tool's: it includes whatever the node
    spent starting up. Close enough for a column that is otherwise blank, and
    never written into the record, where it would pass for the tool's.
    '''
    durations = {}

    for node in job.get("nodes") or []:
        step, index = node.get("step"), node.get("index")
        if not step or index is None or not node.get("terminal"):
            continue
        if not node.get("started_at") or not node.get("finished_at"):
            # A node that never ran -- skipped, or cancelled before it began.
            continue

        started = _epoch(node["started_at"])
        finished = _epoch(node["finished_at"])
        if started is not None and finished is not None and finished >= started:
            durations[(step, index)] = finished - started

    return durations


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


def _why_it_failed(job: Dict[str, Any], help_pages: Optional[str] = None) -> str:
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

    # The server's own page for it, where the server has said it serves them.
    slug = str(error["type"]).rstrip("/").rsplit("/", 1)[-1]
    return describe(error,
                    next_step=NO_NODE_FAILED if ran_out and failed == 0 else None,
                    help_url=f"{help_pages}{slug}" if help_pages else None)


def _is_refusal(problem: ServerProblem) -> bool:
    '''Whether to stop polling.

    🔴 The discriminator is the `type` slug and never the status alone. A 5xx
    with no slug is a server having a bad minute; a named condition is an answer
    that will not change by asking again.
    '''
    if problem.slug is None:
        return False
    return problem.slug not in ("not-ready", "rate-limited")


# The shape of one entry in a version requirement, and the same one
# `Task.check_exe_version` parses: an operator, then a version that may be
# almost anything, because a tool's own versioning is its own business.
_ONE_SPEC = re.compile(r"^\s*(?P<operator>==|!=|<=|>=|<|>|~=)\s*"
                       r"(?P<version>[^,;\s)]*)\s*$")


def _normalize_spec(task, declared: str) -> Optional[str]:
    """One specifier set, with each version put through the task's normaliser.

    A set is comma-separated and every part is normalised on its own, so
    `>=24Q3-2011,<27Q1` survives intact. A part this cannot parse is dropped
    rather than sent raw: an unparsable requirement matches nothing on the far
    side, so passing it on would turn *this server has no version I can read*
    into *this server has no OpenROAD*.
    """
    parts = []
    for one in str(declared).split(","):
        found = _ONE_SPEC.match(one)
        if not found:
            logger.debug(f"dropping an unreadable version requirement: {one!r}")
            return None
        try:
            version = task.normalize_version(found.group("version"))
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"could not normalize {one!r}: {e}")
            return None
        parts.append(f"{found.group('operator')}{version}")

    return ",".join(parts) if parts else None


def _framework_requirement() -> str:
    """What this client needs the server's framework image to hold.

    ⚠️ **`requires`, beside `versions`, and they are not the same statement.**
    `versions` is what this machine HAS -- exact, and what a reproducibility
    record wants. `requires` is what the image must HOLD, as a specifier. They
    happen to agree here, and the reason they agree is below.

    ⚠️ **`tools` is `{}`, and that is the ordinary case.** A client submitting
    remotely generally has no tools installed -- which is usually why it is
    submitting remotely. The bucket is still sent, because it is a closed set
    and an absent one would be a client that did not know about it.

    The SERVER resolves the specifier, which is what lets a deployment answer
    *which image has all of these* -- a question a client cannot answer,
    because `GET /v1`'s `software` is flat per name within a bucket while the
    image join is over combinations.

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

    🔴 **A development version asks by prefix instead.** `0.38.10.dev43+g20db`
    carries a commit in its local segment, so an exact pin from a checkout can
    only ever match an image built from that same commit -- which is nobody's
    image. PEP 440's prefix form covers it and needs no new grammar.

    ⚠️ **The spelling is `==0.38.10.*` and not `==0.38.10.dev*`**: a `.*`
    attaches to the release segment and nothing after it, so the second is
    rejected outright. What the legal one matches is every build of that
    release line, dev ones included -- which is what was wanted.

    ⚠️ A dev job's resolution is therefore not stable between two dev builds,
    which is correct: they are not the same code.
    """
    from packaging.version import InvalidVersion, Version

    try:
        parsed = Version(sc_version)
    except InvalidVersion:
        return f"=={sc_version}"

    if parsed.is_devrelease:
        return f"=={parsed.base_version}.*"
    return f"=={sc_version}"


def _named(asked) -> str:
    '''`upload_sources` as a person reads it.'''
    return ", ".join(f"{item.get('kind')} {item.get('name')} ({item.get('dataroot')})"
                     for item in asked)


def _key() -> str:
    return str(uuid.uuid4())
