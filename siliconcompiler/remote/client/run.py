'''
Running a design somewhere else.

Four calls to start it and one to watch it:

    POST /v1/jobs                     the job exists, and can be refused here
    POST /v1/jobs/{id}/upload-grant   where to put the bytes
    PUT  <the grant's url>            the bytes move, never through the API
    POST /v1/jobs/{id}/submit         carrying the digest of what was PUT
    GET  /v1/jobs/{id}                until `terminal`

🔴 **The refusal comes before the bytes.** That is what the descriptor on the
create body is for, and it is why the job is created before anything is
packed.
'''

import hashlib
import json
import logging
import os
import posixpath
import re
import sys
import shutil
import tarfile
import tempfile
import threading
import time
import uuid

from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler import __version__ as sc_version
from siliconcompiler._common import NodeStatus as SCNodeStatus
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.logging import SCBlankLoggerFormatter
from siliconcompiler.utils.paths import collectiondir, jobdir, workdir

from siliconcompiler.remote.client.errors import (
    NO_NODE_FAILED, RemoteError, ServerProblem, clean, describe)
from siliconcompiler.remote.client import MAX_CANCEL_REASON
from siliconcompiler.remote.client.results import Results, record_job, recorded_job
from siliconcompiler.utils.units import format_binary, format_duration

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

        # What the flow reads (D129): the manifest to upload, carrying every
        # node's `require`, and the keys it names. Worked out once per run --
        # with each node's own Python environment, from the same setup pass.
        self._needed = None
        self._environments = {}
        # Each executed node's task, set up on the copy, with the tool
        # versions it declared; and each node whose setup could not run here.
        self._tasks = {}
        self._failed = {}
        self._upstream_sources = None
        # What the job last said it was, for what an interrupt tells the user.
        self._last_state: Optional[str] = None
        self._owner: Optional[str] = None
        # The job's Python, worked out once: `_python`.
        self._python_worked = None
        # Whether what the job's images hold in place of a listed version was
        # said: `_say_substituted`.
        self._substituted_said = False
        self._wheel_dir: Optional[str] = None
        # The upload report's rows for what the server asked for at create.
        self._asked_rows: list = []
        # Each node's place in the flow, for listing nodes: `_flow_order`.
        self._order: Optional[Dict[Tuple[str, str], int]] = None
        self._python_pins = None
        self._software = None

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
        # 🔴 Everything that would only fail at the server is said here, before
        # a job exists or a byte is packed.
        self._preflight()
        self._preprocess()

        design = self.project.name
        jobname = self.project.option.get_jobname()

        from siliconcompiler.remote import owners

        # 🔴 Created before anything is packed: a refusal at create costs
        # nothing, and the job then names what else to put in the archive.
        flow, node_count = self._flow_descriptor()
        job = self.client.create_job(
            design=design, jobname=jobname,
            run_hash=self._reuse_hash(),
            # Every node this run reads and does not run, whose results are
            # not here and are held by the job that ran it.
            continues_from=self._upstream()[1] or None,
            flow=flow, node_count=node_count,
            # The job's Python packages: what an index can supply, listed here
            # and authoritative; what none can, uploaded as wheels. Either
            # relies on `python.env`, and says so for the refusal before the
            # upload.
            python_packages=self._python()[0],
            needs=["python.env"] if self._python()[0] or self._python()[1] else None,
            requested_versions={"python": self._requested_python(),
                                "tools": self._tool_requirements(),
                                **self._requested_interpreter()},
            # What this machine expects the server to supply. A lookup at the
            # other end, never a fetch, and credentials stripped -- and only
            # what the flow reads.
            sources=[item for item in owners.sources(self.project, self._needs()[1])
                     if tuple(item["keypath"]) not in self._uploaded_packages()] or None,
            idempotency_key=_key())

        job_id = job["id"]
        self.project.set('record', 'remoteid', job_id)
        record_job(jobdir(self.project), job_id)

        if job["state"] in ("completed", "failed"):
            # A job this server already has. Nothing was uploaded and nothing
            # will run; the results are whatever it kept.
            self.logger.info(f"Server returned an existing job: {job_id}")
            return job_id

        self.logger.info(f"Your job's reference ID is: {job_id}")

        # 🔴 Followed, never constructed. The portal's route shape may change
        # without a version bump, so this is printed only when the server sent
        # it -- absent means the deployment has no web UI.
        if job.get("web_url"):
            self.logger.info(f"Watch it at: {job['web_url']}")
            self._open_portal(job["web_url"])

        self._save_manifest()

        try:
            with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
                asked = job.get("upload_sources") or []
                if asked:
                    # 🔴 What the server cannot supply, it asks for (D114):
                    # this machine resolves those with its OWN credentials and
                    # puts them in the archive -- or cancels, naming each.
                    self.logger.info(f"The server asked for {_named(asked)}")
                    self._asked_rows = self._answer(asked, collectiondir(self.project))

                upload = Path(tmpdir) / "upload.tar.gz"
                digest, size = self._pack(upload)

                grant = self.client.upload_grant(job_id, size, digest)
                self._report_upload(size)
                self.client.upload(grant, upload)

                # `202` in `staging`: what staging finds arrives on the job.
                self.client.submit_job(job_id, idempotency_key=_key())
        except BaseException as e:
            self._abandon(job_id, e, why=e.reason if isinstance(e, _CannotSupply) else None)
            raise
        finally:
            self._drop_wheels()

        self.logger.info("Job submitted")
        return job_id

    def _abandon(self, job_id: str, error: BaseException, why: Optional[str] = None) -> None:
        '''Cancel a job that will not be submitted -- an interrupt, an upload
        or submit that failed, or something asked for that cannot be sent -- so
        it holds no slot until it is abandoned.'''
        if why is None:
            why = "interrupted before it was submitted" \
                if isinstance(error, KeyboardInterrupt) else "its upload or submit failed"
        if isinstance(error, _CannotSupply):
            # The items that fit, then how many more: the whole list is what
            # this run already printed.
            reason = _fitted(f"cancelled from sc-remote: {_CannotSupply.LEAD}",
                             error.failures)
        else:
            reason = _fitted("cancelled from sc-remote: ", [why])
        try:
            self.client.cancel_job(job_id, reason=reason)
            self.logger.info(f"Cancelled job {job_id}: {why}")
        except Exception as e:                                   # noqa: BLE001
            self.logger.warning(f"Could not cancel job {job_id}, which was not "
                                f"submitted: {e}")
        # Not a job to reconnect to.
        self.project.unset('record', 'remoteid')

    def _preflight(self) -> None:
        '''What the server would refuse, said here before create.'''
        from siliconcompiler.remote.runflow import runtime_flow

        project = self.project

        # 🔴 The PDK fails closed where the class has a PDK setting.
        if project.valid("asic", "pdk") and not project.get("asic", "pdk"):
            raise RemoteError(
                "this project sets no PDK, and a remote run of an ASIC project needs "
                "one: set it with set_pdk() -- a target usually does -- and run again")

        # A task class no installed distribution provides cannot run anywhere
        # but here: the server runs only what a package provides.
        from importlib import metadata

        provided = metadata.packages_distributions()
        flow = project.get_flow()
        missing = {}
        for step, index in runtime_flow(project).get_nodes():
            name = flow.get_graph_node(step, index).get_taskmodule() or ""
            module = name.split("/", 1)[0]
            top = module.split(".", 1)[0]
            if module == "__main__" or top not in provided:
                missing.setdefault(name, []).append(f"{step}/{index}")
        if missing:
            named = "; ".join(f"{', '.join(nodes)} runs {name}"
                              for name, nodes in sorted(missing.items()))
            raise RemoteError(
                f"a remote run needs every task class from an installed package, and "
                f"these are not: {named}. Move the task into a package, install it "
                "here, and run again")

        self._check_upstream_files()
        self._check_dataroots()
        self._check_software()
        # The node's Python: what cannot be worked out, a compiled extension or
        # two sources for one path among the user's code, and a package to
        # install where the server installs none -- all before create.
        self._check_python_env()
        self._check_account()

    def _check_dataroots(self) -> None:
        '''Stop before create where a dataroot the server would be told of is
        defined where no keypath names it: a server names each by a library's
        or a task's (surface D298), and refuses anything else.'''
        from siliconcompiler.remote import owners

        try:
            owners.sources(self.project, self._needs()[1])
        except owners.Unnamed as e:
            raise RemoteError(str(e)) from None

    def _check_account(self) -> None:
        '''What `GET /v1/me` says of this account, before create: an upcoming
        terms version not yet accepted, named before the submit it would
        refuse -- advisory, the server decides -- and a capability the job's
        Python needs and the account is not granted, which stops the run.'''
        try:
            me = self.client.me()
        except RemoteError:
            return
        self._check_capabilities(me)

    def _check_capabilities(self, me: Dict[str, Any]) -> None:
        '''Stop where the job's Python needs a capability this account does
        not hold (surface *Who may use it: three capabilities*): `python-env`
        to list packages, `python-wheels` to upload wheels.

        Only where `authorized.capabilities` is published: a deployment that
        grants nothing -- sc-server, which has no `authorized` at all -- gates
        nothing, and `python.env` alone decides there. A grant blocked on an
        agreement is not one the job can use yet.'''
        authorized = me.get("authorized") if isinstance(me, dict) else None
        granted = authorized.get("capabilities") if isinstance(authorized, dict) else None
        if not isinstance(granted, list):
            return
        member, built, _ = self._python()
        needed = [name for name, needs in (("python-env", bool(member)),
                                           ("python-wheels", bool(built))) if needs]
        held = {entry.get("name"): entry for entry in granted if isinstance(entry, dict)}
        missing = [name for name in needed if name not in held]
        blocked = [name for name in needed if name in held and held[name].get("blocked_by")]
        if not missing and not blocked:
            return
        what = {"python-env": "to install its Python packages",
                "python-wheels": f"to upload {', '.join(sorted(built))}"}
        said = [f"{name} {what[name]}" for name in missing + blocked]
        # 🔴 Each document in the way, with its own signing link, as the
        # listing's access message says it: `blocked_by` is where to go.
        from siliconcompiler.remote.client.errors import blocked_lines

        titles = {entry.get("id"): entry.get("title")
                  for entry in me.get("terms") or [] if isinstance(entry, dict)}
        signing = [line for name in blocked
                   for line in blocked_lines(held[name].get("blocked_by"), titles)]
        raise RemoteError(
            f"this run's Python needs {' and '.join(said)}, and this account "
            + ("is not granted " + " or ".join(missing) if missing else "")
            + (" and " if missing and blocked else "")
            + (f"holds {' and '.join(blocked)} blocked on an agreement it has not accepted"
               if blocked else "")
            + (": " + "; ".join(signing) if signing else "")
            + ". Ask the deployment for the grant, or accept the agreement")

    def _check_upstream_files(self) -> None:
        '''A `-from` run whose upstream outputs, on this machine, lack a file
        a node in the run reads.'''
        from siliconcompiler.remote.runflow import runtime_flow

        from siliconcompiler.remote import links

        root = jobdir(self.project)
        packed = self._upstream()[0]
        if not packed:
            return
        have = set()
        for outputs in packed:
            where = os.path.join(root, outputs)
            for here, dirs, files in os.walk(where):
                have.update(files)
                # 🔴 A link to nothing is a missing file: most often a
                # pass-through into a node this machine never fetched.
                for name in sorted(dirs + files):
                    full = os.path.join(here, name)
                    if os.path.islink(full) and \
                            links.follow(root, full)[1] == links.DANGLING:
                        raise RemoteError(
                            f"{os.path.relpath(full, root)} is a link to "
                            f"{os.readlink(full)}, which is not on this machine: fetch "
                            "the node it belongs to, or the whole job, or run from an "
                            "earlier step")

        runtime = runtime_flow(self.project)
        flow = self.project.get_flow()
        for step, index in runtime.get_nodes():
            node = flow.get_graph_node(step, index)
            try:
                reads = self.project.get("tool", node.get_tool(), "task", node.get_task(),
                                         "input", step=step, index=index) or []
            except Exception:                                    # noqa: BLE001
                continue
            upstream = [source for source in runtime.get_node_inputs(step, index)
                        if source not in runtime.get_nodes()]
            if not upstream:
                continue
            lacking = sorted(name for name in reads if name not in have)
            if lacking:
                raise RemoteError(
                    f"{step}/{index} reads {', '.join(lacking)}, which the results of "
                    f"{', '.join(f'{s}/{i}' for s, i in upstream)} on this machine do "
                    "not hold. Run from an earlier step")

    def _check_software(self) -> None:
        '''Advisory: a requirement nothing this server advertises satisfies.
        The server decides; this only says so before the upload.'''
        try:
            software = self.client.capabilities().get("software") or {}
        except RemoteError:
            return
        wanted = {"python": self._requested_python(), "tools": self._tool_requirements(),
                  **self._requested_interpreter()}
        for bucket, requirements in wanted.items():
            held = software.get(bucket) or {}
            for name, alternatives in (requirements or {}).items():
                versions = held.get(name)
                if bucket == "interpreter" and versions is not None and not any(
                        _satisfied(versions, spec) for spec in alternatives):
                    self.logger.warning(
                        f"This server's images run Python {', '.join(versions)}, and "
                        f"this job's own Python modules were written for "
                        f"{' or '.join(alternatives)}: the job will be refused until "
                        "the server's operator adds an image with that Python")
                    continue
                if versions is None:
                    self.logger.warning(f"This server advertises no {name}; the job "
                                        "may be refused")
                    continue
                if not alternatives:
                    continue
                # 🔴 Each alternative's matches, never the iterator `filter`
                # returns, which is truthy whatever it holds.
                if not any(_satisfied(versions, spec) for spec in alternatives):
                    self.logger.warning(
                        f"This server advertises {name} {', '.join(versions)}, which "
                        f"does not satisfy {' or '.join(alternatives)}; the job may be "
                        "refused")

    def _needed_from(self, root: str) -> List[str]:
        '''What else of the job directory the run reads, relative to it: the
        collected sources, and the ``outputs/`` of each node a `-from` run
        reads and does not run whose results are on this machine (see
        `_upstream`).'''
        needed = []

        collected = collectiondir(self.project)
        if collected and os.path.isdir(collected):
            needed.append(os.path.relpath(collected, root))

        return needed + self._upstream()[0]

    def _upstream(self) -> Tuple[List[str], List[Dict[str, str]]]:
        '''Where each node a `-from` run reads and does not run gets its
        results from, worked out once (surface D175): ``(packed, continues_from)``.

        - **Its outputs are here** -- a file under ``outputs/`` other than its
          manifest: its ``outputs/`` is packed, so a file changed by hand is
          the one used. A local run switched to remote takes this path.
        - **Only its manifest is here**: the job that ran it is the one this
          client recorded fetching it from (`recorded_job`) -- never read out of
          the manifest, which the server wrote -- and it is named in
          ``continues_from``.
        - **Neither**: refused before anything moves. A node from a local run
          has no job id, so its results must be here.

        The derivation is the server's too (`runflow.upstream_nodes`).
        '''
        if self._upstream_sources is not None:
            return self._upstream_sources

        from siliconcompiler.remote.runflow import outputs_present, upstream_nodes

        # A node skipped in the run it came from is looked through, as the
        # server does from that job's recorded states.
        skipped = [(step, index) for step, index in self.project.get_flow().get_nodes()
                   if self.project.get('record', 'status', step=step, index=index)
                   == SCNodeStatus.SKIPPED]
        try:
            upstream = upstream_nodes(self.project, skipped)
        except Exception as e:                                   # noqa: BLE001
            # A flow that will not resolve fails at the server with a reason;
            # this is only deciding what to send.
            logger.debug(f"could not tell which upstream results to send: {e}")
            upstream = []

        root = jobdir(self.project)
        packed, continued = [], []
        for step, index in upstream:
            node = workdir(self.project, step=step, index=index)
            if outputs_present(node, self.project.name):
                packed.append(os.path.relpath(os.path.join(node, "outputs"), root))
                continue
            ran_in = recorded_job(node)
            if ran_in:
                continued.append({"step": step, "index": index, "job_id": ran_in})
                continue
            raise RemoteError(
                f"this run starts part-way through its flow and reads the results of "
                f"{step}/{index}, which are not on this machine -- neither its outputs "
                "nor a manifest naming the remote job that ran it. Run it first, or "
                "run from an earlier step")
        self._upstream_sources = (packed, continued)
        return self._upstream_sources

    def _report_upload(self, size: int, report=None) -> None:
        '''What goes up, per dataroot, with sizes -- before it goes.

        🔴 Said every time, because what is uploaded is decided by rule rather
        than by the user, and a PDK uploaded by mistake is gigabytes and, for a
        proprietary one, a disclosure.
        '''
        report = self._uploading if report is None else report
        total = format_binary(size, "B", digits=1, show_unit=True, compact=True, default="—")
        self.logger.info(f"Uploading {total}")
        for kind, name, dataroot, weight, files in report:
            where = f" ({dataroot})" if dataroot else ""
            shown = format_binary(weight, "B", digits=1, show_unit=True, compact=True,
                                  default="—")
            self.logger.info(f"  {kind} {name}{where}: {shown}, "
                             f"{files} file{'s' if files != 1 else ''}")

    def _send_asked(self, job_id: str, asked) -> None:
        '''The follow-up for a job sent back to `awaiting_input` (D124): an
        archive of ONLY what the server asked for, its own grant, and submit
        again.'''
        import hashlib

        from siliconcompiler.remote import owners

        seen = tuple(sorted((item.get("kind"), ",".join(item.get("keypath") or ()),
                             item.get("name") or "") for item in asked))
        if seen in self._sent:
            raise RemoteError(f"the server asked again for {_named(asked)}, which "
                              "this client has already sent")
        self._sent.add(seen)

        self.logger.info(f"The server could not supply {_named(asked)}; sending it")
        with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
            collection = Path(tmpdir) / "sc_collected_files"
            try:
                report = self._answer(asked, str(collection), only_asked=True)
            except _CannotSupply as e:
                self._abandon(job_id, e, why=e.reason)
                raise

            upload = Path(tmpdir) / "follow-up.tar.gz"
            with tarfile.open(upload, mode="w:gz") as tar:
                tar.add(str(collection), arcname="sc_collected_files")

            digest, size = hashlib.sha256(), 0
            with open(upload, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)

            grant = self.client.upload_grant(job_id, size, f"sha256:{digest.hexdigest()}")
            self._report_upload(size, owners.upload_report(self.project, collection) + report)
            self.client.upload(grant, upload)
            self.client.submit_job(job_id, idempotency_key=_key())

    def _open_portal(self, web_url: str) -> None:
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
        and lands on the job (client-v1-migration D17).

        🔴 **Landing on `web_url`'s own path**, never one built from the job
        id: the route is the portal's, and only the server knows its shape. A
        CI session never asks, since nobody is at a browser; and where the
        handover is refused -- a `404` from a deployment with no such route
        included -- the page opens as given, and the reason is said.
        '''
        from urllib.parse import urlsplit

        if self.client.ci_session:
            return
        wanted = self.client.credentials.get("open_portal")
        if wanted is False:
            return
        if not wanted:
            if self.project.option.get_nodisplay():
                return
            if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
                return

        try:
            self.client.portal(open_browser=True, landing=urlsplit(web_url).path)
        except Exception as e:                                   # noqa: BLE001
            # A handover that is not given is not a reason to stop a run.
            why = (str(e).strip().splitlines() or [type(e).__name__])[0]
            self.logger.warning(f"The server did not hand this browser a session "
                                f"({why}); opening the job's page as given")
            self.client.open_url(web_url, "the job's page")

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

    def _needs(self):
        '''``(manifest project, required keys)``, worked out once per run.

        🔴 **The owner table says whether a value MAY go up; this says whether
        the flow NEEDS it (D129).** `require` is empty until setup runs, so
        every node is set up here on a copy and the result carried in the
        manifest -- which is where the server reads the same set from.

        ⚠️ A setup that cannot run here -- a task needing what only its image
        has -- leaves the set unknown: every file goes up by owner alone, as it
        did before, and the manifest carries nothing for the server to check.
        '''
        from siliconcompiler.remote import owners

        if self._needed is None:
            try:
                worked = owners.work_out(self.project)
            except Exception as e:                               # noqa: BLE001
                self.logger.warning(
                    f"Could not work out which files the flow reads ({e}); "
                    "uploading every file this machine may send")
                self._needed = (self.project, None)
                return self._needed

            # 🔴 Each node on its own: one setup that cannot run here drops no
            # other node's Python. The set of files the flow reads is
            # then unknown, so every file goes up by owner alone.
            self._environments = worked.environments
            self._tasks = worked.tasks
            self._failed = worked.failed
            if worked.failed:
                named = ", ".join(f"{step}/{index}" for step, index in sorted(worked.failed))
                self.logger.warning(
                    f"Could not work out which files {named} read; uploading every "
                    "file this machine may send")
                self._needed = (self.project, None)
            else:
                carried = owners.with_required(self.project, worked.required)
                self._needed = (carried, owners.required(carried))
        return self._needed

    def _requested_interpreter(self) -> Dict[str, Dict[str, List[str]]]:
        '''`requested_versions.interpreter`: the major and minor version of
        the Python running here, `==3.12.*`, for a job with a node that runs
        the user's own Python -- whose modules were written and checked against
        it -- and nothing for any other job (surface D293).'''
        self._needs()
        if not self._environments:
            return {}
        return {"interpreter": {"python": [f"=={sys.version_info[0]}."
                                           f"{sys.version_info[1]}.*"]}}

    def _requested_python(self) -> Dict[str, List[str]]:
        '''`requested_versions.python`, the fixed list (surface *The descriptor*):
        `siliconcompiler`; the distribution behind each executed node's task
        class; each framework distribution a task declares, at the range
        SiliconCompiler declares for it; a distribution whose installed-package
        dataroot the server supplies, where `software` lists it at this
        version; and one holding a private dataroot. Each exact, a framework
        distribution excepted.'''
        if self._python_pins is None:
            from siliconcompiler.remote import owners
            from siliconcompiler.remote.runflow import runtime_flow

            project, required = self._needs()
            pins = {"siliconcompiler": [_framework_requirement()]}

            def exact(distribution):
                name = _canonical(distribution)
                if name in pins:
                    return
                try:
                    pins[name] = [_pin(metadata.version(distribution))]
                except metadata.PackageNotFoundError:
                    return

            installed = metadata.packages_distributions()
            flow = project.get_flow()
            framework = {name for env in self._environments.values()
                         for name in env.framework}
            for step, index in runtime_flow(project).get_nodes():
                module = (flow.get_graph_node(step, index).get_taskmodule() or "")
                for distribution in installed.get(module.split("/", 1)[0]
                                                  .split(".", 1)[0], ()):
                    exact(distribution)
                # Declared on the class, so it is named whether or not the
                # node's setup can run here.
                try:
                    framework.update(flow.get_task_module(step, index)
                                     .framework_distributions())
                except Exception:                                # noqa: BLE001
                    pass

            for name in sorted(framework):
                declared = _framework_range(name)
                # Any version, where neither SiliconCompiler nor this machine
                # says which.
                pins[_canonical(name)] = [declared] if declared else []

            for _, distribution in owners.installed_dataroots(project, required):
                if self._supplied(distribution):
                    exact(distribution)

            for distribution in sorted(owners.private_holders(project, required)):
                exact(distribution)

            self._python_pins = pins
        return self._python_pins

    def _supplied(self, distribution: str) -> bool:
        '''Whether the server lists ``distribution`` at the version installed
        here, so it can supply that package's dataroots itself.'''
        from packaging.version import InvalidVersion, Version

        if self._software is None:
            try:
                self._software = self.client.capabilities().get("software") or {}
            except RemoteError:
                self._software = {}
        listed = (self._software.get("python") or {}).get(_canonical(distribution)) or []
        try:
            mine = Version(metadata.version(distribution))
            return any(Version(version) == mine for version in listed)
        except (InvalidVersion, metadata.PackageNotFoundError):
            return False

    def _uploaded_packages(self):
        '''The keypath of each dataroot from an installed package the
        server does not list at this version: its files upload.'''
        from siliconcompiler.remote import owners

        project, required = self._needs()
        return {entry for entry, distribution in owners.installed_dataroots(project, required)
                if not self._supplied(distribution)}

    def _python(self):
        '''The job's Python, worked out once (surface *A node's own Python
        packages, built while staging*): ``(python_packages or None, {wheel
        file name: its path here}, {path under the collection directory: the
        file here})``.

        🔴 The client always builds the lists and the user never does: each
        distribution the run's Python imports, or a task loads by name, at the
        version installed here, and each distribution those and the wheels
        depend on as a constraint -- less every `requested_versions.python`
        name, which the image holds, and every distribution no index can
        supply, which goes up as a wheel built here. The user's own modules go up as files, in their
        test's collected folder. No index is named, and no pip configuration
        is read.

        ⚠️ Constraints alone install nothing, so a job whose Python imports no
        installed distribution and carries no wheel sends no `python_packages`
        and needs no `python.env`: a testbench of only its own modules runs
        anywhere its image holds cocotb.
        '''
        if self._python_worked is not None:
            return self._python_worked

        from siliconcompiler.remote import owners
        from siliconcompiler.remote.client import capture, wheels

        self._needs()
        self._check_worked_out()
        if not self._environments:
            self._python_worked = (None, {}, {})
            return self._python_worked

        excluded = self._not_sent_roots()
        tests = sorted({os.path.abspath(source) for wanted in self._environments.values()
                        for source in wanted.sources})
        collected = owners.collected_paths(self.project, tests)

        roots: Dict[str, set] = {}
        helpers: Dict[str, str] = {}
        for (step, index), wanted in sorted(self._environments.items()):
            try:
                found = capture.reach(wanted.sources, wanted.requirements)
            except capture.CannotForward as e:
                raise RemoteError(f"{step}/{index}: {e}") from None
            for warning in found.warnings:
                self.logger.warning(f"{step}/{index}: {warning}")
            for name, extras in found.distributions.items():
                roots.setdefault(name, set()).update(extras)
            for test, files in sorted(found.helpers.items()):
                # A private or supplied dataroot brings its own helpers.
                if any(test == root or test.startswith(root + os.sep) for root in excluded):
                    continue
                where = collected.get(test)
                if where is None:
                    self.logger.warning(
                        f"{step}/{index}: {test} is not a file this project names, so "
                        "the modules beside it that it imports are not sent")
                    continue
                folder = posixpath.dirname(where)
                for relative, path in sorted(files.items()):
                    try:
                        capture.place(helpers, f"{folder}/{relative}", path,
                                      f"{step}/{index}'s helper module {relative}")
                    except capture.CannotForward as e:
                        raise RemoteError(f"{step}/{index}: {e}") from None

        try:
            listed = capture.lists(roots, self._requested_python())
        except capture.CannotForward as e:
            raise RemoteError(str(e)) from None
        for warning in listed.warnings:
            self.logger.warning(warning)

        # 🔴 Built before create: a distribution with a compiled file, or a
        # build that fails, stops the run before anything exists.
        built: Dict[str, str] = {}
        if listed.wheels:
            self._wheel_dir = tempfile.mkdtemp(prefix="sc-remote-wheels-")
            for dist in listed.wheels:
                try:
                    path = wheels.build(dist, self._wheel_dir, warn=self.logger.warning)
                except capture.CannotForward as e:
                    self._drop_wheels()
                    raise RemoteError(str(e)) from None
                built[os.path.basename(path)] = path

        member = None
        if listed.requirements or built:
            member = {"requirements": [f"{name}=={version}"
                                       for name, version in listed.requirements],
                      "constraints": [f"{name}=={version}"
                                      for name, version in listed.constraints]}
        self.logger.info(
            f"Python packages: {len(listed.requirements)} to install"
            + (f" under {len(listed.constraints)} constraints" if member else "")
            + f", {len(built)} built as wheels, and {len(helpers)} of your own files "
            "sent beside the tests")
        self._python_worked = (member, built, helpers)
        return self._python_worked

    def _drop_wheels(self) -> None:
        if self._wheel_dir:
            shutil.rmtree(self._wheel_dir, ignore_errors=True)
            self._wheel_dir = None

    def _check_worked_out(self) -> None:
        '''Stop before create where a node the run executes runs the user's
        Python and its setup could not run here: what it imports cannot be
        worked out, and a node missing a package fails only on the server.'''
        from siliconcompiler.remote.runflow import runtime_flow
        from siliconcompiler.tool import Task

        if not self._failed:
            return
        flow = self.project.get_flow()
        executed = set(runtime_flow(self.project).get_nodes())
        for (step, index), why in sorted(self._failed.items()):
            if (step, index) not in executed:
                continue
            try:
                task = flow.get_task_module(step, index)
            except Exception:                                    # noqa: BLE001
                continue
            if getattr(task, "get_python_environment", None) is not \
                    Task.get_python_environment:
                raise RemoteError(
                    f"{step}/{index} runs your own Python, and what it needs cannot be "
                    f"worked out here, because its setup failed: {why}")

    def _check_python_env(self) -> None:
        '''Stop before create where the job has Python packages to install and
        the server installs none.'''
        member, built, _ = self._python()
        if not member and not built:
            return
        try:
            features = self.client.capabilities().get("features") or []
        except RemoteError:
            return
        if "python.env" in features:
            return
        named = (member or {}).get("requirements", []) + sorted(built)
        raise RemoteError(
            f"this run's Python needs {', '.join(named)} installed, and this server "
            "does not install a job's Python packages (it lists no python.env)")

    def _not_sent_roots(self) -> List[str]:
        '''Directories whose files reach a node through their own dataroot --
        private ones, and installed packages the server supplies -- and so are
        never sent as the user's own code.'''
        from siliconcompiler.remote import owners

        roots = []
        project, required = self._needs()
        supplied = {entry for entry, distribution
                    in owners.installed_dataroots(project, required)
                    if self._supplied(distribution)}
        for one in owners._values(project):
            if one.origin == owners.PRIVATE or one.keypath in supplied:
                resolver = one.resolvers.get(one.dataroot)
                try:
                    path = resolver.get_path() if resolver is not None else None
                except Exception:                                # noqa: BLE001
                    path = None
                if path:
                    roots.append(str(path))
        return sorted(set(roots))

    def _collect(self, asked=(), directory=None, only_asked: bool = False) -> None:
        '''Collect by owner -- plus, where the server asked, those sources too
        -- and of either, only what the flow reads.

        ``asked`` is an `upload_sources` list, and an entry there selects the
        required values under that dataroot, never all of it. A private
        dataroot is never collected, asked or not: it must not leave this
        machine.

        🔴 **Per value** (`owners.collection`): the rest of a selected value's
        parameter stays behind, and a private value beside it stays on this
        machine.
        '''
        from siliconcompiler.remote import owners

        # 🔴 By keypath, never the dataroot's name alone: many owners use
        # SiliconCompiler's default, `root`, and two tasks of one tool may each
        # have one of the same name (surface D298).
        wanted = {tuple(item.get("keypath") or ())
                  for item in asked if item.get("kind") == "dataroot"}
        required = self._needs()[1]
        # An installed package the server does not list at this version
        # supplies none of its dataroots: they upload, in the first archive.
        if not only_asked:
            wanted |= self._uploaded_packages()

        def pick(one) -> bool:
            if not owners.needed(one.key, required):
                return False
            if not only_asked and owners.uploads(self.project, one.key, one.dataroot,
                                                 one.resolvers, one.value.get()):
                return True
            return one.keypath in wanted

        chosen = owners.collection(self.project, pick)
        try:
            collect(self.project, keys=chosen.keys, directory=directory,
                    verbose=directory is None, select=chosen.select,
                    whitelist=list(self.client.credentials.directory_whitelist))
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

        🔴 **No manifest in it carries a credential** (surface D302): every
        dataroot's path, the history's included, goes without its userinfo and
        with every query value masked -- in the manifest at its root and in
        each upstream node's own. The archive is kept on the server as the
        job's `input`, and anyone who can read the job can read that. Each is a
        masked copy, written aside: the user's own manifests keep what they
        registered.
        '''
        from siliconcompiler.remote import owners

        root = jobdir(self.project)
        manifest = f"{self.project.name}.pkg.json"

        # The job's wheels and the user's helper modules go where the server
        # looks for them: in the collection, beside what `collect` put there.
        collected = collectiondir(self.project)
        placed = []
        if collected and (self._python()[1] or self._python()[2]):
            os.makedirs(collected, exist_ok=True)
            placed = self._place_python(collected)

        packed = self._upstream()[0]
        with tempfile.TemporaryDirectory(prefix="sc-remote-") as scratch:
            # The copy carrying every node's `require`, so the server reads the
            # set this archive was filtered by out of the manifest it came with.
            sent = os.path.join(scratch, manifest)
            _uploadable(self._needs()[0]).write_manifest(sent)
            replaced = self._upstream_manifests(root, packed, scratch)

            with tarfile.open(upload, mode="w:gz") as tar:
                tar.add(sent, arcname=manifest)
                outputs = _LinkPacker(tar, root, packed, self.logger, replaced=replaced)
                for name in self._needed_from(root):
                    if name in packed:
                        outputs.add(name)
                    else:
                        tar.add(os.path.join(root, name), arcname=name)

        self._uploading = (owners.upload_report(self.project, collected)
                           if collected and os.path.isdir(collected) else []) + placed \
            + self._asked_rows
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

    def _upstream_manifests(self, root: str, packed, scratch: str) -> Dict[str, str]:
        '''Each upstream node's manifest the archive carries that holds a
        credential, as ``{its real path: a masked copy under scratch}``, for
        `_LinkPacker` to send in its place. One that holds none goes as it is.'''
        from siliconcompiler import Project

        replaced = {}
        for n, name in enumerate(packed):
            path = os.path.join(root, name, f"{self.project.name}.pkg.json")
            if not os.path.isfile(path):
                continue
            try:
                held = Project.from_manifest(filepath=path)
            except Exception as e:                               # noqa: BLE001
                # 🔴 Fails closed: what cannot be read cannot be told free of
                # a credential.
                raise RemoteError(
                    f"{name}/{self.project.name}.pkg.json could not be read, so this "
                    f"client cannot tell that it carries no credential: {e}") from None
            cleaned = _uploadable(held)
            if cleaned is held:
                continue
            copy = os.path.join(scratch, f"upstream-{n}.pkg.json")
            cleaned.write_manifest(copy)
            replaced[os.path.realpath(path)] = copy
        return replaced

    def _place_python(self, collection: str):
        '''The job's wheels and the user's helper modules, into the
        collection directory before it is packed: each wheel under
        `sc_collected_files/python/`, and each helper in its test's collected
        folder, keeping its name. A helper `collect` already put there is a
        file the project names, and is left as it is. Returns the upload
        report's rows for them.'''
        from siliconcompiler.remote import environment

        _, built, helpers = self._python()
        rows = []
        weight = files = 0
        for relative, source in sorted(helpers.items()):
            target = os.path.join(collection, *relative.split("/"))
            if os.path.exists(target):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
            weight += os.path.getsize(target)
            files += 1
        if files:
            rows.append(("python", "helper modules", None, weight, files))
        for name, path in sorted(built.items()):
            target = os.path.join(collection, environment.WHEELS, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(path, target)
            rows.append(("python package", environment.wheel_name(name), None,
                         os.path.getsize(target), 1))
        return rows

    def _answer(self, asked, collection: str, only_asked: bool = False) -> list:
        '''Everything the server asked for, into ``collection``, or nothing
        (surface D287): each dataroot fetched with this machine's own
        credentials, and each Python package's wheel repacked from what is
        installed here. Returns the upload report's rows for the wheels.

        🔴 **Never a partial answer.** Every item is tried before anything is
        collected, and one that cannot be had -- a source this machine cannot
        reach either, a package that is not installed here or holds a compiled
        file -- raises _CannotSupply naming every one that failed, which the
        caller cancels the job with. Nothing is uploaded.
        '''
        from siliconcompiler.remote import environment

        failures = []
        for item in asked:
            if item.get("kind") == "dataroot":
                why = self._unreachable(item)
                if why:
                    failures.append(f"the dataroot {','.join(item.get('keypath') or ())}: "
                                    f"{why}")

        wheel_dir = tempfile.mkdtemp(prefix="sc-remote-asked-")
        try:
            built = []
            for item in asked:
                if item.get("kind") == "python":
                    try:
                        built.append((item.get("name"), self._wheel_asked(item, wheel_dir)))
                    except _Unsupplied as e:
                        failures.append(str(e))
            if failures:
                raise _CannotSupply(failures)

            if any(item.get("kind") == "dataroot" for item in asked):
                try:
                    self._collect(asked, directory=collection, only_asked=only_asked)
                except (FileNotFoundError, OSError, RuntimeError, ValueError,
                        RemoteError) as e:
                    raise _CannotSupply([_scrubbed(str(e) or type(e).__name__)]) from None

            rows = []
            for name, path in built:
                target = os.path.join(collection, environment.WHEELS, os.path.basename(path))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(path, target)
                rows.append(("python package", name, None, os.path.getsize(target), 1))
            return rows
        finally:
            shutil.rmtree(wheel_dir, ignore_errors=True)

    def _unreachable(self, item) -> Optional[str]:
        '''Why an asked-for dataroot cannot be had here either, with any
        credential taken out of it; None where it can.'''
        from siliconcompiler.remote import owners

        wanted = tuple(item.get("keypath") or ())
        resolver = None
        for one in owners._values(self.project):
            if one.keypath == wanted:
                resolver = one.resolvers.get(one.dataroot)
                break
        else:
            return "this project names no such dataroot"
        if resolver is None:
            return None
        try:
            path = resolver.get_path()
        except Exception as e:                                   # noqa: BLE001
            return f"it cannot be fetched here either: {_scrubbed(str(e) or type(e).__name__)}"
        if not path or not os.path.exists(str(path)):
            return "it is not on this machine either"
        return None

    def _wheel_asked(self, item, folder: str) -> str:
        '''The wheel of a Python package the server asked for (surface *How
        it is built*: a package no configured index has), repacked from what
        is installed here. Raises _Unsupplied.'''
        from siliconcompiler.remote.client import capture, wheels

        name = item.get("name") or ""
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            raise _Unsupplied(f"the Python package {name}: it is not installed here "
                              "either") from None
        try:
            return wheels.build(dist, folder, warn=self.logger.warning)
        except capture.CannotForward as e:
            if e.compiled:
                raise _Unsupplied(f"the Python package {name}: it holds a compiled file, "
                                  f"{e.compiled}, built for this machine") from None
            raise _Unsupplied(f"the Python package {name}: "
                              f"{str(e).splitlines()[0]}") from None

    def _run_hash(self) -> Optional[str]:
        '''This run's hash for job reuse, or None -- which it always is today.

        🔴 **Nothing computes one yet.** What SiliconCompiler should hash is
        its own decision (run-hash.md), and a hash wrong in the direction of
        *the same* hands back a result produced by different work.
        '''
        return None

    def _reuse_hash(self) -> Optional[str]:
        '''The hash to send, where there is one and the server reuses jobs.

        Only to a deployment advertising `jobs.reuse`: elsewhere the member is
        validated and ignored, and sending it would claim a reuse nobody does.
        A hit comes back as the job already there, which `_start` returns
        without a grant or an upload.
        '''
        run_hash = self._run_hash()
        if not run_hash:
            return None
        try:
            features = self.client.capabilities().get("features") or []
        except RemoteError:
            return None
        if "jobs.reuse" not in features:
            return None
        built = self._python()[1]
        if not built:
            return run_hash
        # 🔴 Each uploaded wheel's digest, which a hash of the work cannot
        # know: a wheel is built here from whatever its source holds now, and
        # the same version is often different code.

        def digest(path) -> str:
            found = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    found.update(chunk)
            return found.hexdigest()

        return hashlib.sha256(json.dumps(
            {"run_hash": run_hash,
             "wheels": sorted(digest(path) for path in built.values())},
            sort_keys=True).encode()).hexdigest()

    def _flow_descriptor(self) -> Tuple[Optional[str], Optional[int]]:
        '''The flowgraph's name and how many nodes the run has: what the
        server can refuse us on before the upload moves.

        Advisory, re-derived at submit, and refusing to build it is never worth
        failing the run over -- a sparse descriptor is legal and costs only the
        check it would have answered.
        '''
        try:
            from siliconcompiler.remote.runflow import runtime_nodes

            flow = self.project.get_flow()
            return flow.name, len(runtime_nodes(self.project))
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"no flow descriptor: {e}")
            return None, None

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
            from siliconcompiler.remote.runflow import node_tools, runtime_nodes

            self._needs()
            flow = self.project.get_flow()
            for node, tool in node_tools(flow, runtime_nodes(self.project)).items():
                if not tool:
                    continue
                for one in self._declared_versions(node):
                    if one not in wanted.setdefault(tool, []):
                        wanted[tool].append(one)
                wanted.setdefault(tool, [])
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"no tool requirements: {e}")
            return {}

        return wanted

    def _declared_versions(self, node) -> List[str]:
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

        🔴 **From the worked-out copy**, where the node's setup ran: a task
        declares its version requirement inside `setup()`, so a fresh task
        declares nothing. A node whose setup could not run here says `[]`,
        *any version*, which still names the tool.
        """
        held = self._tasks.get(tuple(node))
        if held is None:
            return []
        task, declared = held

        found = []
        for one in declared:
            normalized = _normalize_spec(task, one)
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
        warned = False
        while True:
            try:
                self._poll(job_id)
                return
            except KeyboardInterrupt:
                # 🔴 Not yet `queued` (surface D166): the server may still ask
                # this machine for a source, and with nobody here to send it the
                # job waits until it is abandoned. Said once; a second
                # interrupt leaves.
                if not warned and self._last_state in _NOT_YET_SUBMITTED:
                    warned = True
                    self.logger.warning(
                        f"Job {job_id} is not fully submitted yet (it is "
                        f"{self._last_state}): if the server asks this machine for a "
                        "source and nobody is here to send it, the job waits until it "
                        "is abandoned. Press Ctrl-C again to leave anyway.")
                    continue
                manifest = os.path.join(jobdir(self.project), REMOTE_MANIFEST)
                self.logger.info("Disconnecting from remote job")
                self.logger.info(
                    f"To reconnect to this job use: sc-remote -cfg {manifest} -reconnect")
                # Offered only to whoever may: a job read through a project can
                # belong to somebody else.
                me = self.client.credentials.user_id
                if not (self._owner and me and self._owner != me):
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
                self._last_state = job.get("state")
                owner = job.get("owner")
                self._owner = owner.get("id") if isinstance(owner, dict) else None
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
            self._say_substituted(job)
            tails.follow(job_id, job)

            if job.get("terminal"):
                break

            self._report(job, changed)
            time.sleep(retry_after or DEFAULT_POLL_SECONDS)

        tails.finish()
        self._finish(job, results)

    def _say_substituted(self, job: Dict[str, Any]) -> None:
        '''Once the job has staged, each Python package this machine listed
        that the job's images hold at another version -- the newest of its
        release line, where the listed one does not install there or is
        yanked, or the image's own copy -- beside the version listed here.

        Said once, from `resolved_versions`, and only by the process that
        listed them: the job object does not echo `python_packages`. Where
        nodes run on the host there are no images, and the staging record says
        it (`remote-staging.log`).'''
        from packaging.version import InvalidVersion, Version

        if self._substituted_said or job.get("state") in _NOT_YET_SUBMITTED:
            return
        member = self._python_worked[0] if self._python_worked else None
        held = (job.get("resolved_versions") or {}).get("python")
        if not member or not isinstance(held, dict):
            return
        self._substituted_said = True
        held = {_canonical(name): versions for name, versions in held.items()
                if isinstance(versions, list) and versions}

        def same(one, other) -> bool:
            try:
                return Version(one) == Version(other)
            except InvalidVersion:
                return one == other

        for entry in member["requirements"] + member["constraints"]:
            name, _, listed = entry.partition("==")
            versions = held.get(_canonical(name))
            if versions and not any(same(listed, str(version)) for version in versions):
                self.logger.warning(
                    f"This job runs {name} {', '.join(str(one) for one in versions)}, "
                    f"in place of {listed} as installed here")

    def _record(self, job: Dict[str, Any], seen) -> list:
        '''Write what the server says into this project's record.

        Returns the nodes whose state moved since the last poll, which is all
        the output a dashboard run needs: the dashboard is already showing
        every node's state, so repeating the whole table each poll is noise
        over the top of it.

        ⚠️ **In the order they moved, not the order the server lists them.**
        A poll often carries a node finishing and the one it unblocked
        starting, and the server lists nodes by name: printed as listed, a
        node would start before the one it waits on finished. So each is
        placed by when it reached its state, where the server says -- its
        finish, or its start -- and by its place in the flow otherwise.

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
                changed.append((_moved_at(node), step, index, node.get("state")))
            seen[(step, index)] = status

        order = self._flow_order()

        def moved(item):
            when, step, index, _ = item
            place = order.get((step, index), len(order))
            return (0, when, place) if when else (1, place)

        return [(step, index, state) for _, step, index, state in sorted(changed, key=moved)]

    def _flow_order(self) -> Dict[Tuple[str, str], int]:
        '''Each node's place in the flow's execution order, worked out once:
        how nodes are listed where nothing says when they moved.'''
        if self._order is None:
            order: Dict[Tuple[str, str], int] = {}
            try:
                for layer in self.project.get_flow().get_execution_order():
                    for step, index in layer:
                        order.setdefault((step, index), len(order))
            except Exception as e:                               # noqa: BLE001
                logger.debug(f"no flow order to list nodes in: {e}")
            self._order = order
        return self._order

    def _report(self, job: Dict[str, Any], changed=None) -> None:
        with self.output_lock:
            self._report_locked(job, changed)

    def _report_locked(self, job: Dict[str, Any], changed=None) -> None:
        if self._dashboard():
            # 🔴 The dashboard is already rendering every node's state, so the
            # full table underneath it is the same information twice. What it
            # cannot show is the moment something moved, and why a node failed.
            details = _node_details(job)
            for step, index, state in changed or []:
                said = details.get((step, index)) if state == "failed" else None
                self.logger.info(f"  {step}/{index} -> {state}" + (f": {said}" if said else ""))
            return

        # In the flow's order, not the server's, which is by name.
        order = self._flow_order()
        by_state: Dict[str, list] = {}
        for node in sorted(job.get("nodes") or [], key=lambda node: order.get(
                (node.get("step"), node.get("index")), len(order))):
            by_state.setdefault(node.get("state", "unknown"), []).append(node)

        progress = job.get("progress") or {}
        self.logger.info(
            f"Job is still running ({_state_line(job)}): "
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

        # Each failed node, and why, where the server said: the limit it ran
        # into, or the image that would not pull (surface §17, *A node's
        # `error`*). In the flow's order, since the last poll's moves are never
        # reported on their own.
        order = self._flow_order()
        for (step, index), said in sorted(
                _node_details(job).items(),
                key=lambda item: order.get(item[0], len(order))):
            self.logger.error(f"  {step}/{index} failed: {said}")

        # 🔴 Retrieved on EVERY terminal state, not only on success. A failed
        # run is the one whose log and manifest a user most wants, and a client
        # that fetches nothing when a job fails has hidden the evidence at the
        # moment it became useful.
        results = results or Results(self.project, self.client)
        try:
            results.fetch(job["id"])
            # 🔴 The local job directory is the whole job: a node this run
            # continued from, whose outputs are not here, from the job that ran
            # it -- what is fetchable now, so a caller approved since then gets
            # the files.
            for entry in self._upstream()[1]:
                results.fetch_node(entry["job_id"], entry["step"], entry["index"])
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
        except ServerProblem as refusal:
            if refusal.slug == "not-ready":
                # The node had not started when `/logs` was asked. Transient:
                # the next poll asks again.
                self._started.discard((step, index))
            else:
                logger.debug(f"stopped tailing {step}/{index}: {refusal}")
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


def _state_line(job: Dict[str, Any]) -> str:
    '''The job's state as a person reads it: how long it has been in it, from
    the last entry of `transitions` (surface §17), and why -- the live
    staging phase, or the reason the job entered its state, such as a
    cancel's.'''
    state = str(job.get("state"))
    last = (job.get("transitions") or [{}])[-1]
    entered = _epoch(last.get("at")) if last.get("state") == job.get("state") else None
    if entered is not None:
        state += f" for {format_duration(max(0, time.time() - entered))}"
    reason = job.get("state_reason") or (last.get("reason")
                                         if last.get("state") == job.get("state") else None)
    return state + (f", {clean(str(reason))}" if reason else "")


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


def _node_details(job: Dict[str, Any]) -> Dict[Tuple[str, str], str]:
    '''Each failed node's `error.detail`, as a person reads it: display only,
    and never branched on.'''
    found = {}
    for node in job.get("nodes") or []:
        error = node.get("error")
        if node.get("state") == "failed" and isinstance(error, dict) and error.get("detail"):
            found[(node.get("step"), node.get("index"))] = clean(str(error["detail"]))
    return found


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
    # `run-interrupted` says resubmitting may work, and it would be no less
    # true for a run that got halfway.
    failed = (job.get("progress") or {}).get("failed_count")
    ran_out = str(error["type"]).rstrip("/").rsplit("/", 1)[-1] == "run-failed"

    # The server's own page for it, where the server has said it serves them.
    slug = str(error["type"]).rstrip("/").rsplit("/", 1)[-1]
    return describe(error,
                    next_step=NO_NODE_FAILED if ran_out and failed == 0 else None,
                    help_url=f"{help_pages}{slug}" if help_pages else None,
                    job_id=job.get("id"))


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
    from packaging.specifiers import InvalidSpecifier, SpecifierSet

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

    if not parts:
        return None
    joined = ",".join(parts)
    try:
        # PEP 440, or it matches nothing on the far side.
        SpecifierSet(joined)
    except InvalidSpecifier:
        logger.debug(f"dropping a requirement that is not PEP 440: {joined!r}")
        return None
    return joined


def _satisfied(versions, spec: str) -> bool:
    '''Whether any of ``versions`` meets one PEP 440 specifier set.'''
    from packaging.specifiers import InvalidSpecifier, SpecifierSet

    try:
        return any(SpecifierSet(spec).filter(versions, prereleases=True))
    except InvalidSpecifier:
        return True


class _LinkPacker:
    '''The ``outputs/`` of the upstream nodes an upload carries: links as
    links, and each file once (contract.md, *An upload keeps links, and stores
    a linked file once*; client-v1-migration D4).

    - a link whose chain ends inside the job's build directory at a file or
      directory the archive holds is one link to it, however many hops;
    - where what it ends at is in the build directory and not in the archive,
      it is stored once, at its first appearance, and every later link to it
      points at that copy;
    - a regular file sharing an inode with one already packed is a tar hard
      link to the first;
    - a link whose chain leaves the build directory, or names nothing, is not
      followed: it is left out, and named.

    Nothing is copied in place of a link: some tools keep links in their own
    databases, and copying their targets could upload terabytes.
    '''

    def __init__(self, tar, root: str, packed, logger, replaced=None):
        from siliconcompiler.remote import links

        self.tar, self.root, self.logger = tar, root, logger
        # A file sent as another's bytes, by its real path: an upstream
        # manifest, masked (`RemoteRun._upstream_manifests`).
        self.replaced: Dict[str, str] = dict(replaced or {})
        self.real_root = os.path.realpath(root)
        # Each hard-linked file's home, so a chain ending at a node's
        # `inputs/x` -- the same inode as the upstream `outputs/x` -- points
        # there whatever order the nodes are packed in.
        self.homes = links.Homes(root)
        self.packed = [os.path.realpath(os.path.join(root, name)) for name in packed]
        # What is stored here, by its real path and by inode, and where.
        self.stored: Dict[str, str] = {}
        self.inodes: Dict[Tuple[int, int], str] = {}

    def holds(self, real: str) -> bool:
        return any(real == top or real.startswith(top + os.sep) for top in self.packed)

    def add(self, name: str) -> None:
        self._add_dir(os.path.join(self.root, name), name)

    def _add_dir(self, path: str, arcname: str) -> None:
        import stat
        import time

        info = tarfile.TarInfo(arcname)
        info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, time.time()
        self.tar.addfile(info)
        for name in sorted(os.listdir(path)):
            full, member = os.path.join(path, name), f"{arcname}/{name}"
            held = os.lstat(full)
            if stat.S_ISLNK(held.st_mode):
                self._add_link(full, member)
            elif stat.S_ISDIR(held.st_mode):
                self.stored.setdefault(os.path.realpath(full), member)
                self._add_dir(full, member)
            elif stat.S_ISREG(held.st_mode):
                self._add_file(full, member, held)

    def _add_file(self, path: str, arcname: str, held) -> None:
        import stat

        instead = self.replaced.get(os.path.realpath(path))
        if instead is not None:
            # Its own bytes, never a link to another name for the same inode:
            # that would send what was masked here.
            info = tarfile.TarInfo(arcname)
            info.size, info.mtime = os.path.getsize(instead), held.st_mtime
            info.mode = stat.S_IMODE(held.st_mode)
            with open(instead, "rb") as handle:
                self.tar.addfile(info, handle)
            self.stored.setdefault(os.path.realpath(path), arcname)
            return

        key = (held.st_dev, held.st_ino)
        if held.st_nlink > 1 and key in self.inodes:
            info = tarfile.TarInfo(arcname)
            info.type, info.linkname = tarfile.LNKTYPE, self.inodes[key]
            self.tar.addfile(info)
            return
        info = tarfile.TarInfo(arcname)
        info.size, info.mtime = held.st_size, held.st_mtime
        info.mode = stat.S_IMODE(held.st_mode)
        with open(path, "rb") as handle:
            self.tar.addfile(info, handle)
        self.inodes[key] = arcname
        self.stored.setdefault(os.path.realpath(path), arcname)

    def _add_link(self, path: str, arcname: str) -> None:
        from siliconcompiler.remote import links

        end, why = links.follow(self.root, path)
        if end is None:
            if why == links.DANGLING:
                self.logger.warning(f"{arcname} is a link to nothing, and is not sent")
            else:
                self.logger.warning(f"{arcname} is a link out of the build directory, "
                                    "and is not sent")
            return
        held = os.lstat(end)
        if os.path.isfile(end) and held.st_nlink > 1:
            end = self.homes.home(held) or end
        if self.holds(end):
            self._write_link(arcname, links.relative(end, os.path.realpath(
                os.path.dirname(path))))
            return
        first = self.stored.get(end) or self.inodes.get((held.st_dev, held.st_ino))
        if first is not None:
            # Stored once already: this link points at that copy.
            self._write_link(arcname, os.path.relpath(first, os.path.dirname(arcname))
                             .replace(os.sep, "/"))
            return
        if os.path.isdir(end):
            self.stored[end] = arcname
            self._add_dir(end, arcname)
        else:
            self._add_file(end, arcname, held)

    def _write_link(self, arcname: str, target: str) -> None:
        info = tarfile.TarInfo(arcname)
        info.type, info.linkname = tarfile.SYMTYPE, target
        self.tar.addfile(info)


def _uploadable(project):
    '''`owners.without_credentials`, or a refusal the user reads.'''
    from siliconcompiler.remote import owners

    try:
        return owners.without_credentials(project)
    except ValueError as e:
        raise RemoteError(str(e)) from None


# A job the server may still need this machine for.
_NOT_YET_SUBMITTED = ("created", "awaiting_input", "staging")


def _canonical(name: str) -> str:
    from packaging.utils import canonicalize_name
    return canonicalize_name(name)


def _framework_range(name: str) -> str:
    """The range SiliconCompiler declares for a framework distribution --
    cocotb's, in its `cocotb` extra -- or, where it declares none, the version
    installed here.

    🔴 **A range, not a pin**: the image's version within it runs, and the
    simulator and SiliconCompiler's own process load that one copy.
    """
    from packaging.requirements import InvalidRequirement, Requirement

    for line in metadata.requires("siliconcompiler") or []:
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if _canonical(requirement.name) == _canonical(name) and str(requirement.specifier):
            return str(requirement.specifier)
    try:
        return _pin(metadata.version(name))
    except metadata.PackageNotFoundError:
        return ""


def _framework_requirement() -> str:
    """What this client needs the server's framework image to hold.

    ⚠️ **`tools` beside it is often `{}`, and that is the ordinary case.** A
    client submitting remotely generally has no tools installed -- which is
    usually why it is submitting remotely -- and a tool's requirement comes
    from its task's declared version, which is set in setup.

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
    return _pin(sc_version)


def _pin(version: str) -> str:
    """One installed version as the specifier a server resolves: exact, or
    the release line's prefix for a development build."""
    from packaging.version import InvalidVersion, Version

    try:
        parsed = Version(version)
    except InvalidVersion:
        return f"=={version}"

    if parsed.is_devrelease:
        return f"=={parsed.base_version}.*"
    return f"=={version}"


# What the server takes as a cancel's reason, at most (surface D288).
_MAX_REASON = MAX_CANCEL_REASON

# What a cancel's reason may not hold.
_UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# A URL's `user:secret@`, wherever it sits in a message.
_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")


def _scrubbed(text: str) -> str:
    '''A message with every URL's credentials taken out: what is said to the
    server, and to whoever reads the job, never carries one.'''
    return _USERINFO.sub(r"\1", text)


class _Unsupplied(Exception):
    '''One asked-for item this machine cannot supply, and why.'''


class _CannotSupply(RemoteError):
    '''What the server asked for and this machine cannot supply, each item
    and why. ``reason`` is what the job is cancelled with (surface D287).'''

    LEAD = "it cannot supply what the server asked for: "

    def __init__(self, failures):
        self.failures = list(failures)
        self.reason = self.LEAD + "; ".join(failures)
        super().__init__("the server asked for what this machine cannot supply, so the "
                         "job is cancelled:\n" + "\n".join(f"  {one}" for one in failures))


def _fitted(lead: str, items: List[str], limit: int = _MAX_REASON) -> str:
    '''``lead`` and as many of ``items`` as fit within ``limit`` characters,
    then *and N more* for the rest (surface D288). An item that would not fit
    even alone is cut, so the reason names something. One line: the server
    takes no control character, so each item is made one first.'''
    items = [" ".join(_UNPRINTABLE.sub(" ", str(item)).split()) for item in items]
    for count in range(len(items), 0, -1):
        rest = len(items) - count
        tail = f"; and {rest} more" if rest else ""
        text = lead + "; ".join(items[:count]) + tail
        if len(text) <= limit:
            return text
    rest = len(items) - 1
    tail = f"; and {rest} more" if rest else ""
    room = limit - len(lead) - len(tail) - 3
    return lead + items[0][:max(room, 0)] + "..." + tail


def _moved_at(node: Dict[str, Any]):
    '''When a node reached the state it is in, where the job object says: a
    finished node's finish, a running one's start; None otherwise, or where
    the time cannot be read.'''
    from datetime import datetime, timezone

    if node.get("terminal"):
        when = node.get("finished_at")
    elif node.get("state") == "running":
        when = node.get("started_at")
    else:
        return None
    if not isinstance(when, str):
        return None
    try:
        # `fromisoformat` takes a trailing Z only from 3.11.
        parsed = datetime.fromisoformat(when[:-1] + "+00:00" if when.endswith("Z") else when)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _named(asked) -> str:
    '''`upload_sources` as a person reads it.'''
    return ", ".join(f"the dataroot {','.join(item.get('keypath') or ())}"
                     if item.get("kind") == "dataroot" else
                     f"the Python package {item.get('name')}"
                     for item in asked)


def _key() -> str:
    return str(uuid.uuid4())
