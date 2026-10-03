'''Run a project on a remote server: four calls to start it, one to watch it.

    POST /v1/jobs                     the job exists, and can be refused here
    POST /v1/jobs/{id}/upload-grant   where to put the bytes
    PUT  <the grant's url>            the bytes move, never through the API
    POST /v1/jobs/{id}/submit         no body: the grant bound the digest
    GET  /v1/jobs/{id}                until `terminal`

The job is created before anything is packed, so a refusal comes before the bytes.
'''

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

from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from siliconcompiler import __version__ as sc_version
from siliconcompiler._common import NodeStatus as SCNodeStatus
from siliconcompiler.utils import file_digest
from siliconcompiler.utils.curation import collect
from siliconcompiler.utils.logging import SCBlankLoggerFormatter
from siliconcompiler.utils.paths import collectiondir, jobdir, workdir

from siliconcompiler.remote.client.errors import (
    NO_NODE_FAILED, RemoteError, ServerProblem, _slug, clean, describe)
from siliconcompiler.remote.client import MAX_CANCEL_REASON, _UNPRINTABLE
from siliconcompiler.remote.client.results import Results, record_job, recorded_job
from siliconcompiler.remote.environment import canonical
from siliconcompiler.utils.units import format_binary, format_duration

__all__ = ["RemoteRun", "REMOTE_MANIFEST"]


logger = logging.getLogger(__name__)


# What a reconnect reads, beside the job's manifest: reconnect and cancel take a path.
REMOTE_MANIFEST = "sc_remote.pkg.json"

# Only a fallback: the server sets the pace with `Retry-After`.
DEFAULT_POLL_SECONDS = 5

# Server errors are transient and retried, but not forever.
MAX_TRANSIENT_POLLS = 20

MAX_LINE = 70


# The contract's node states as SiliconCompiler's. An unknown state is not an error:
# the loop reads `terminal`, so a new state is additive.
_NODE_STATES = {
    "pending": SCNodeStatus.PENDING,
    "queued": SCNodeStatus.QUEUED,
    # Fetching its image: waiting, not running, so a slow pull does not read as a hang.
    "preparing": SCNodeStatus.QUEUED,
    "running": SCNodeStatus.RUNNING,
    "completed": SCNodeStatus.SUCCESS,
    "failed": SCNodeStatus.ERROR,
    "skipped": SCNodeStatus.SKIPPED,
    # Never ran and never will; SiliconCompiler has no closer state.
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

        # The tails' threads and the poll loop share a console whose formatter
        # is swapped per line.
        self.output_lock = threading.Lock()

        # Requests already answered, so a repeated ask fails instead of looping.
        self._uploading = []
        self._sent = set()

        # What the flow reads (D129), worked out once with each node's Python.
        self._needed = None
        self._environments = {}
        self._tasks = {}
        self._failed = {}
        self._upstream_sources = None
        self._last_state: Optional[str] = None
        self._owner: Optional[str] = None
        self._python_worked = None
        self._substituted_said = False
        self._wheel_dir: Optional[str] = None
        self._asked_rows: list = []
        self._order: Optional[Dict[Tuple[str, str], int]] = None
        self._python_pins = None
        self._software = None

    def run(self) -> None:
        if self.project.get('arg', 'step') or self.project.get('arg', 'index'):
            raise RemoteError(
                "a remote run cannot be narrowed with [arg,step] or [arg,index]: "
                "the whole flow is submitted as one job")

        # Before anything is packed: there is no default server address.
        self.client.transport

        resume = (not self.project.option.get_clean()
                  and self.project.get('record', 'remoteid'))

        if resume:
            job_id = self.project.get('record', 'remoteid')
            self.logger.info(f"Reconnecting to job {job_id}")
        else:
            job_id = self._start()

        self._watch(job_id)

    def _start(self) -> str:
        self._preflight()
        self._collect()

        design = self.project.name
        jobname = self.project.option.get_jobname()

        from siliconcompiler.remote import owners

        # Created before packing: the job names what else the archive must hold.
        flow, node_count = self._flow_descriptor()
        job = self.client.create_job(
            design=design, jobname=jobname,
            continues_from=self._upstream()[1] or None,
            flow=flow, node_count=node_count,
            # Listed packages and uploaded wheels both need `python.env`.
            python_packages=self._python()[0],
            needs=["python.env"] if self._python()[0] or self._python()[1] else None,
            requested_versions={"python": self._requested_python(),
                                "tools": self._tool_requirements(),
                                **self._requested_interpreter()},
            # What the server should supply: looked up there, never fetched,
            # credentials stripped.
            sources=[item for item in owners.sources(self.project, self._needs()[1])
                     if tuple(item["keypath"]) not in self._uploaded_packages()] or None)

        job_id = job["id"]
        self.project.set('record', 'remoteid', job_id)
        record_job(jobdir(self.project), job_id)

        self.logger.info(f"Your job's reference ID is: {job_id}")

        self._open_portal(job_id)

        self.project.write_manifest(os.path.join(jobdir(self.project), REMOTE_MANIFEST))

        try:
            with tempfile.TemporaryDirectory(prefix="sc-remote-") as tmpdir:
                asked = job.get("upload_sources") or []
                if asked:
                    # D114: sent with this machine's OWN credentials, or cancelled.
                    self.logger.info(f"The server asked for {_named(asked)}")
                    self._asked_rows = self._answer(asked, collectiondir(self.project))

                upload = Path(tmpdir) / "upload.tar.gz"
                digest, size = self._pack(upload)

                grant = self.client.upload_grant(job_id, size, digest)
                self._report_upload(size)
                self.client.upload(grant, upload)

                self.client.submit_job(job_id)
        except BaseException as e:
            self._abandon(job_id, e)
            raise
        finally:
            self._drop_wheels()

        self.logger.info("Job submitted")
        return job_id

    def _abandon(self, job_id: str, error: BaseException) -> None:
        '''Cancel a job that will not be submitted, so it holds no slot until abandoned.'''
        if isinstance(error, _CannotSupply):
            why = error.reason
            reason = _fitted(f"cancelled from sc-remote: {_CannotSupply.LEAD}",
                             error.failures)
        else:
            why = "interrupted before it was submitted" \
                if isinstance(error, KeyboardInterrupt) else "its upload or submit failed"
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

        # The PDK fails closed where the class has a PDK setting.
        if project.valid("asic", "pdk") and not project.get("asic", "pdk"):
            raise RemoteError(
                "this project sets no PDK, and a remote run of an ASIC project needs "
                "one: set it with set_pdk() -- a target usually does -- and run again")

        # The server runs only task classes an installed package provides.
        from siliconcompiler.remote.client import capture

        provided = capture._module_distributions()
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
        self._check_python_env()
        self._check_account()

    def _check_dataroots(self) -> None:
        '''Stop where a dataroot the server would be told of has no library or
        task keypath naming it (surface D298): the server refuses it.'''
        from siliconcompiler.remote import owners

        try:
            owners.sources(self.project, self._needs()[1])
        except owners.Unnamed as e:
            raise RemoteError(str(e)) from None

    def _check_account(self) -> None:
        '''Check the account (`GET /v1/me`) before create: unaccepted terms are
        named, and a missing capability stops the run.'''
        try:
            me = self.client.me()
        except RemoteError:
            return
        self._check_capabilities(me)

    def _check_capabilities(self, me: Dict[str, Any]) -> None:
        '''Stop where the job's Python needs `python-packages` or `python-wheels`
        and the account lacks it or holds it blocked on an agreement.

        Only where `authorized.capabilities` is published: sc-server grants
        nothing, so `python.env` alone decides there.'''
        authorized = me.get("authorized") if isinstance(me, dict) else None
        granted = authorized.get("capabilities") if isinstance(authorized, dict) else None
        if not isinstance(granted, list):
            return
        member, built, _ = self._python()
        needed = [name for name, needs in (("python-packages", bool(member)),
                                           ("python-wheels", bool(built))) if needs]
        held = {entry.get("name"): entry for entry in granted if isinstance(entry, dict)}
        missing = [name for name in needed if name not in held]
        blocked = [name for name in needed if name in held and held[name].get("blocked_by")]
        if not missing and not blocked:
            return
        what = {"python-packages": "to install its Python packages",
                "python-wheels": f"to upload {', '.join(sorted(built))}"}
        said = [f"{name} {what[name]}" for name in missing + blocked]
        # `blocked_by` holds `terms` ids: name each document by its title.
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
        '''Stop a `-from` run whose local upstream outputs lack a file it reads.'''
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
                # A dangling link is a missing file, usually into a node never fetched.
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
        '''Warn of a requirement nothing this server advertises satisfies; the server decides.'''
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
                # Test matches, never `filter`'s iterator, which is always truthy.
                if not any(_satisfied(versions, spec) for spec in alternatives):
                    self.logger.warning(
                        f"This server advertises {name} {', '.join(versions)}, which "
                        f"does not satisfy {' or '.join(alternatives)}; the job may be "
                        "refused")

    def _needed_from(self, root: str) -> List[str]:
        '''What else of the job directory to pack, relative to it: the collected
        sources and the local upstream ``outputs/`` (`_upstream`).'''
        needed = []

        collected = collectiondir(self.project)
        if collected and os.path.isdir(collected):
            needed.append(os.path.relpath(collected, root))

        return needed + self._upstream()[0]

    def _upstream(self) -> Tuple[List[str], List[Dict[str, str]]]:
        '''Where each node a `-from` run reads but does not run gets its results
        (surface D175), worked out once, as ``(packed, continues_from)``:

        - outputs here: its ``outputs/`` is packed, so a hand-edited file is used;
        - only its manifest here: named in ``continues_from`` with the job this
          client recorded fetching it from (`recorded_job`), never the manifest's;
        - neither: refused before anything moves.
        '''
        if self._upstream_sources is not None:
            return self._upstream_sources

        from siliconcompiler.remote.runflow import outputs_present, upstream_nodes

        # Skipped nodes are looked through, as the server does.
        skipped = [(step, index) for step, index in self.project.get_flow().get_nodes()
                   if self.project.get('record', 'status', step=step, index=index)
                   == SCNodeStatus.SKIPPED]
        try:
            upstream = upstream_nodes(self.project, skipped)
        except Exception as e:                                   # noqa: BLE001
            # An unresolvable flow fails at the server, with a reason.
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
        '''Log what goes up, per dataroot, with sizes, before it goes.

        Every time: a rule decides what uploads, and a PDK sent by mistake is
        gigabytes and, if proprietary, a disclosure.'''
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
        '''Answer a job sent back to `awaiting_input` (D124): an archive of ONLY
        what was asked for, its own grant, and submit again.'''
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
                self._abandon(job_id, e)
                raise

            upload = Path(tmpdir) / "follow-up.tar.gz"
            with tarfile.open(upload, mode="w:gz") as tar:
                tar.add(str(collection), arcname="sc_collected_files")

            grant = self.client.upload_grant(job_id, os.path.getsize(upload),
                                             f"sha256:{file_digest(upload).hexdigest()}")
            self._report_upload(os.path.getsize(upload),
                                owners.upload_report(self.project, collection) + report)
            self.client.upload(grant, upload)
            self.client.submit_job(job_id)

    def _open_portal(self, job_id: str) -> None:
        '''Open the job's page where a person is plainly watching.

        Provisional (surface D309): deleting this method and its one call removes it.

        The page comes from `POST /v1/auth/browser`, never built, and opens only
        outside CI, without `option,nodisplay`, and with stdout a terminal.
        The `open_portal` preference overrides the last two either way.
        '''
        if self.client.ci_session:
            return
        from siliconcompiler.remote.client.credentials import preference

        wanted = preference("open_portal")
        if wanted is False:
            return
        if not wanted:
            if self.project.option.get_nodisplay():
                return
            if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
                return

        self.client.open_page("the job's page", require_tty=False, job_id=job_id)

    def _needs(self):
        '''``(manifest project, required keys)``, worked out once per run.

        The owner table says whether a value MAY go up; this says whether the
        flow NEEDS it (D129), carried in the manifest for the server to read.
        Where a setup cannot run here the set is None: every file goes up by owner.
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

            # Per node: one setup failing here drops no other node's Python.
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
        '''`requested_versions.interpreter` (surface D293): this Python as
        `==3.12.*`, only for a job running the user's own Python, written against it.'''
        self._needs()
        if not self._environments:
            return {}
        return {"interpreter": {"python": [f"=={sys.version_info[0]}."
                                           f"{sys.version_info[1]}.*"]}}

    def _requested_python(self) -> Dict[str, List[str]]:
        '''`requested_versions.python` (surface *The descriptor*): siliconcompiler,
        each executed task's distribution, each declared framework at its range,
        each distribution whose dataroot the server supplies, and each holder of
        a private dataroot. Exact pins, frameworks excepted.'''
        if self._python_pins is None:
            from siliconcompiler.remote import owners
            from siliconcompiler.remote.client import capture
            from siliconcompiler.remote.runflow import runtime_flow

            project, required = self._needs()
            pins = {"siliconcompiler": [_pin(sc_version)]}

            def exact(distribution):
                name = canonical(distribution)
                if name in pins:
                    return
                try:
                    pins[name] = [_pin(metadata.version(distribution))]
                except metadata.PackageNotFoundError:
                    return

            installed = capture._module_distributions()
            flow = project.get_flow()
            framework = {name for env in self._environments.values()
                         for name in env.framework}
            for step, index in runtime_flow(project).get_nodes():
                module = (flow.get_graph_node(step, index).get_taskmodule() or "")
                for distribution in installed.get(module.split("/", 1)[0]
                                                  .split(".", 1)[0], ()):
                    exact(distribution)
                # Declared on the class, so named even where setup cannot run here.
                try:
                    framework.update(flow.get_task_module(step, index)
                                     .framework_distributions())
                except Exception:                                # noqa: BLE001
                    pass

            for name in sorted(framework):
                declared = _framework_range(name)
                pins[canonical(name)] = [declared] if declared else []

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
        listed = (self._software.get("python") or {}).get(canonical(distribution)) or []
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
        '''The job's Python, worked out once (surface *A node's own Python packages,
        built while staging*): ``(python_packages or None, {wheel: path here},
        {collected path: helper file here})``.

        Always built by the client: imported distributions at their installed
        versions, their dependencies as constraints, less what the image holds;
        what no index has goes up as a wheel. No index is named, no pip config read.
        With no requirement and no wheel it sends nothing and needs no `python.env`.
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

        # Built before create, so a compiled file or failed build stops the run first.
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
        '''Stop where an executed node runs the user's Python and its setup failed
        here: its imports cannot be worked out.'''
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
        '''Directories reaching a node through their own dataroot (private, or
        server-supplied), so never sent as the user's code.'''
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
        '''Collect what the flow reads: by owner, plus what the server asked for.

        The design always; a PDK's, library's, device's or tool's files only
        where local or editable (`owners`). No flag is consulted, `copy=True`
        included: the server holds what is left out or refuses at submit.

        ``asked`` (`upload_sources`) selects required values under its dataroots.
        Per value (`owners.collection`); a private dataroot is never collected.
        '''
        from siliconcompiler.remote import owners

        # By keypath, never name: many owners share the default `root` (D298).
        wanted = {tuple(item.get("keypath") or ())
                  for item in asked if item.get("kind") == "dataroot"}
        required = self._needs()[1]
        if not only_asked:
            wanted |= self._uploaded_packages()

        def pick(one) -> bool:
            if not owners.needed(one.key, required):
                return False
            if not only_asked and owners.uploads(self.project, one.key, one.dataroot,
                                                 one.resolvers):
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
            # Unreachable here too: fail naming it, and upload nothing.
            raise RemoteError(
                f"the server asked for {_named(asked)}, and this machine cannot "
                f"reach it either: {e}") from None

    def _pack(self, upload: Path) -> Tuple[str, int]:
        '''Pack the manifest and what the server needs of the job directory.

        Named entries only: a reused job directory holds old logs, fetched
        nodes and the `job.log` this run is appending to.
        No manifest in it carries a credential (surface D302): anyone who can
        read the job reads its `input`, so each manifest goes as a masked copy.
        '''
        from siliconcompiler.remote import owners

        root = jobdir(self.project)
        manifest = f"{self.project.name}.pkg.json"

        collected = collectiondir(self.project)
        placed = []
        if collected and (self._python()[1] or self._python()[2]):
            os.makedirs(collected, exist_ok=True)
            placed = self._place_python(collected)

        packed = self._upstream()[0]
        with tempfile.TemporaryDirectory(prefix="sc-remote-") as scratch:
            # Carries every node's `require`: the set this archive was filtered by.
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
            # In the archive now, and the largest thing here: keep no second copy.
            shutil.rmtree(collected, ignore_errors=True)

        return f"sha256:{file_digest(upload).hexdigest()}", os.path.getsize(upload)

    def _upstream_manifests(self, root: str, packed, scratch: str) -> Dict[str, str]:
        '''Each packed upstream manifest holding a credential, as ``{real path:
        masked copy under scratch}`` for `_LinkPacker` to send instead.'''
        from siliconcompiler import Project

        replaced = {}
        for n, name in enumerate(packed):
            path = os.path.join(root, name, f"{self.project.name}.pkg.json")
            if not os.path.isfile(path):
                continue
            try:
                held = Project.from_manifest(filepath=path)
            except Exception as e:                               # noqa: BLE001
                # Fails closed.
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
        '''Copy the wheels (under `python/`) and helper modules (beside their test)
        into the collection; return their upload-report rows. A helper `collect`
        already placed is left as it is.'''
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
        '''Put everything the server asked for into ``collection``, or nothing
        (surface D287); return the wheels' upload-report rows.

        Never a partial answer: every item is tried first, and any failure
        raises _CannotSupply naming each, which cancels the job.
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
        '''Repack an asked-for Python package's wheel from what is installed here.'''
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

    def _flow_descriptor(self) -> Tuple[Optional[str], Optional[int]]:
        '''The flow's name and node count, for a refusal before the upload.
        Advisory and re-derived at submit, so failing to build it is never fatal.'''
        try:
            from siliconcompiler.remote.runflow import runtime_nodes

            flow = self.project.get_flow()
            return flow.name, len(runtime_nodes(self.project))
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"no flow descriptor: {e}")
            return None, None

    def _tool_requirements(self) -> Dict[str, Any]:
        """Each tool the flow uses, with its version requirements.

        The server derives the same list at submit; this only moves a refusal
        BEFORE the upload. Each value is a list of alternative specifier sets,
        as `check_exe_version` reads them; empty means any version.
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
        """One node's declared version requirements for its tool.

        Normalised with the task's own `normalize_version`, as
        `check_exe_version` does: OpenROAD's `>=24Q3-2011` is not PEP 440, and
        sent raw the server would refuse a satisfying image.
        From the worked-out copy, since a task declares its version in
        `setup()`; a node whose setup failed here says `[]`, any version.
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

    def reconnect(self, job_id: str) -> None:
        '''Re-enter the wait for a job that is already running.

        The only way back after Ctrl-C, so the job id is recorded before the upload.
        '''
        self._watch(job_id)

    def _watch(self, job_id: str) -> None:
        warned = False
        while True:
            try:
                self._poll(job_id)
                return
            except KeyboardInterrupt:
                # Not yet `queued` (D166): the server may still ask this
                # machine for a source. Said once; a second interrupt leaves.
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
                # A job read through a project can be somebody else's.
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
                # The `type` slug decides, never the status: a slugless 5xx
                # is transient, a named condition will not change.
                if refusal.slug is not None and \
                        refusal.slug not in ("not-ready", "rate-limited"):
                    # AS A FAILURE: falling through would announce an empty finished job.
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
                # Sent back for a source; not terminal, so the wait goes on.
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
        '''Once staged, warn of each listed Python package the job runs at another
        version. Once, from `resolved_versions`, and only by the process that
        listed them: the job object does not echo `python_packages`.'''
        from packaging.version import InvalidVersion, Version

        if self._substituted_said or job.get("state") in _NOT_YET_SUBMITTED:
            return
        member = self._python_worked[0] if self._python_worked else None
        held = (job.get("resolved_versions") or {}).get("python")
        if not member or not isinstance(held, dict):
            return
        self._substituted_said = True
        held = {canonical(name): versions for name, versions in held.items()
                if isinstance(versions, list) and versions}

        def same(one, other) -> bool:
            try:
                return Version(one) == Version(other)
            except InvalidVersion:
                return one == other

        for entry in member["requirements"] + member["constraints"]:
            name, _, listed = entry.partition("==")
            versions = held.get(canonical(name))
            if versions and not any(same(listed, str(version)) for version in versions):
                self.logger.warning(
                    f"This job runs {name} {', '.join(str(one) for one in versions)}, "
                    f"in place of {listed} as installed here")

    def _record(self, job: Dict[str, Any], seen) -> list:
        '''Write the server's node states into the record; return the nodes that moved.

        In the order they moved, not the server's (by name), so a node never
        starts before the one it waits on finished: by finish or start time where
        given, else flow order. Tolerant: an unreadable node is skipped.
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
            return (0, when, place) if when is not None else (1, place)

        return [(step, index, state) for _, step, index, state in sorted(changed, key=moved)]

    def _flow_order(self) -> Dict[Tuple[str, str], int]:
        '''Each node's place in the flow's execution order, worked out once.'''
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
            if self._dashboard():
                # The dashboard shows every state; say only what moved, and why it failed.
                details = _node_details(job)
                for step, index, state in changed or []:
                    said = details.get((step, index)) if state == "failed" else None
                    self.logger.info(f"  {step}/{index} -> {state}"
                                     + (f": {said}" if said else ""))
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

        Without this it never rereads the record. ``starttimes`` come from
        ``started_at``, an instant, so a timer survives polls, reconnects and restarts.
        '''
        board = self._dashboard()
        if board is None:
            return

        try:
            board.update_manifest({"starttimes": _starttimes(job),
                                   "durations": _durations(job)})
        except Exception as e:                                   # noqa: BLE001
            # A failed repaint must not end the run.
            logger.debug(f"could not update the dashboard: {e}")

    def _dashboard(self):
        '''The dashboard this run is being watched through, if any.'''
        board = getattr(self.project, "_Project__dashboard", None)
        try:
            return board if board is not None and board.is_running() else None
        except Exception:                                        # noqa: BLE001
            return None

    def _finish(self, job: Dict[str, Any], results: Results) -> None:
        state = job.get("state")

        if state == "completed":
            self.logger.info("Remote job completed")
        elif job.get("error"):
            self.logger.error(f"Remote job {state}: "
                              f"{_why_it_failed(job, self.client.transport.help_pages)}")
        else:
            self.logger.error(f"Remote job {state}")

        # Each failed node and why (surface §17, *A node's `error`*), in flow order.
        order = self._flow_order()
        for (step, index), said in sorted(
                _node_details(job).items(),
                key=lambda item: order.get(item[0], len(order))):
            self.logger.error(f"  {step}/{index} failed: {said}")

        # On EVERY terminal state: a failed run's log is the one most wanted.
        try:
            results.fetch(job["id"])
            # The local job directory is the whole job: fetch each node this
            # run continued from, from the job that ran it.
            for entry in self._upstream()[1]:
                results.fetch_node(entry["job_id"], entry["step"], entry["index"])
        except ServerProblem as e:
            self.logger.error(str(e))
        except RemoteError as e:
            self.logger.error(f"Could not retrieve results: {e}")

        # So a later summary() or show() is not narrowed by a finished run.
        self.project.option.unset('remote')

        if state != "completed":
            raise RemoteError(f"the remote job ended {state}")


class _Tails:
    '''The live logs of whatever is running, on this terminal.

    One stream for the whole job where the server offers `logs.stream.job`,
    else one per running node up to ``concurrent_log_streams``. Each line
    carries ``job | step | index``, so interleaved they read like a local run.
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

        self._enabled, self._ceiling, self._whole_job = self._decide()

    def _decide(self) -> Tuple[bool, int, bool]:
        '''``(tail at all, how many at once, as one job stream)``. Off when the
        caller asked for quiet, `GET /v1` is unreadable, or no live tail is served.'''
        if self._run.project.option.get_quiet():
            return False, 0, False

        try:
            capabilities = self._client.capabilities()
        except RemoteError as e:
            logger.debug(f"no capabilities, so no tailing: {e}")
            return False, 0, False

        features = capabilities.get("features") or []
        if "logs.stream" not in features:
            # Absent means unsupported; the archived log still comes with the results.
            return False, 0, False

        ceiling = (capabilities.get("limits") or {}).get("concurrent_log_streams")
        return True, max(1, int(ceiling or 1)), "logs.stream.job" in features

    def follow(self, job_id: str, job: Dict[str, Any]) -> None:
        '''Start a tail for anything newly running.'''
        if not self._enabled:
            return

        if self._whole_job:
            # Opened once something runs: before that the job form answers `not-ready`.
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
                # Permanent: follow each node from the next poll, never asking again.
                logger.debug("no job stream here; following each node instead")
                self._whole_job = False
            elif refusal.slug == "not-ready":
                # Transient: the next poll asks again.
                self._started.discard(JOB)
            else:
                logger.debug(f"stopped following the job's log: {refusal}")
        except Exception as e:                                   # noqa: BLE001
            # The log is still fetched with the results.
            logger.debug(f"stopped following the job's log: {e}")
        finally:
            with self._lock:
                self._threads.pop(JOB, None)

    def _tail(self, job_id: str, step: str, index: str) -> None:
        try:
            self._client.tail_log(job_id, step, index, write=self._write)
        except ServerProblem as refusal:
            if refusal.slug == "not-ready":
                # Transient: the next poll asks again.
                self._started.discard((step, index))
            else:
                logger.debug(f"stopped tailing {step}/{index}: {refusal}")
        except Exception as e:                                   # noqa: BLE001
            # Must not disturb the run or the other tails; the log comes with the results.
            logger.debug(f"stopped tailing {step}/{index}: {e}")
        finally:
            with self._lock:
                self._threads.pop((step, index), None)

    def _write(self, text: str) -> None:
        '''Print a chunk of a node's log on the shared terminal.

        With a blank formatter: the lines already carry ``job | step | index``,
        and this run's prefix would stamp on top. The dashboard formats with the
        console handler's formatter, so one swap covers both.
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
        '''Let the tails drain, bounded: each log is in the results anyway.'''
        for thread in list(self._threads.values()):
            thread.join(timeout=timeout)
        self._stop.set()


# The job stream thread's key: no flow has this (step, index).
JOB = (None, None)


def _starttimes(job: Dict[str, Any]) -> Dict[Tuple[str, str], float]:
    '''When each running node started, as ``{(step, index): epoch seconds}``.'''
    starttimes = {}

    for node in job.get("nodes") or []:
        step, index = node.get("step"), node.get("index")
        started = node.get("started_at")
        if not step or index is None or not started:
            continue

        if node.get("terminal"):
            # A finished node must stop counting: the board ticks these against now.
            continue

        moment = _epoch(started)
        if moment is not None:
            starttimes[(step, index)] = moment

    return starttimes


def _durations(job: Dict[str, Any]) -> Dict[Tuple[str, str], float]:
    '''How long each finished node took, as the server saw it.

    Here before the node's manifest, which may never come; the board prefers
    `metric,tasktime` once it does. Server wall time, startup included, so
    never written into the record.
    '''
    durations = {}

    for node in job.get("nodes") or []:
        step, index = node.get("step"), node.get("index")
        if not step or index is None or not node.get("terminal"):
            continue
        if not node.get("started_at") or not node.get("finished_at"):
            # Never ran: skipped, or cancelled first.
            continue

        started = _epoch(node["started_at"])
        finished = _epoch(node["finished_at"])
        if started is not None and finished is not None and finished >= started:
            durations[(step, index)] = finished - started

    return durations


def _state_line(job: Dict[str, Any]) -> str:
    '''The job's state as a person reads it: for how long (from `transitions`,
    surface §17), and why.'''
    state = str(job.get("state"))
    last = (job.get("transitions") or [{}])[-1]
    entered = _epoch(last.get("at")) if last.get("state") == job.get("state") else None
    if entered is not None:
        state += f" for {format_duration(max(0, time.time() - entered))}"
    reason = job.get("state_reason") or (last.get("reason")
                                         if last.get("state") == job.get("state") else None)
    return state + (f", {clean(str(reason))}" if reason else "")


def _epoch(timestamp: str) -> Optional[float]:
    '''An RFC 3339 instant as epoch seconds; None if unreadable, which costs a timer.'''
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

    A `run-failed` with no failed node gets `NO_NODE_FAILED`: only that
    slug's advice names a node.
    '''
    error = job.get("error") or {}
    if not error.get("type"):
        return "no reason given"

    failed = (job.get("progress") or {}).get("failed_count")
    slug = _slug(error)

    return describe(error,
                    next_step=NO_NODE_FAILED if slug == "run-failed" and failed == 0
                    else None,
                    help_url=f"{help_pages}{slug}" if help_pages else None,
                    job_id=job.get("id"))


# One specifier as `Task.check_exe_version` parses it: a tool's version can be anything.
_ONE_SPEC = re.compile(r"^\s*(?P<operator>==|!=|<=|>=|<|>|~=)\s*"
                       r"(?P<version>[^,;\s)]*)\s*$")


def _normalize_spec(task, declared: str) -> Optional[str]:
    """One specifier set, each part's version put through the task's normaliser.

    An unparsable set is dropped, not sent raw: it would match nothing on the
    server, turning *no readable version* into *no OpenROAD*.
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
    '''Pack upstream ``outputs/`` with links as links and each file once
    (contract.md, *An upload keeps links, and stores a linked file once*).

    A link into the archive stays one link; one into the build directory but
    not the archive stores its target once; a hard link stays a tar hard link;
    one leaving the build directory, or dangling, is left out and named. A
    link's target is never copied in its place: that could upload terabytes.
    '''

    def __init__(self, tar, root: str, packed, logger, replaced=None):
        from siliconcompiler.remote import links

        self.tar, self.root, self.logger = tar, root, logger
        # Masked upstream manifests to send instead (`RemoteRun._upstream_manifests`).
        self.replaced: Dict[str, str] = dict(replaced or {})
        self.real_root = os.path.realpath(root)
        # So a link to a node's `inputs/x` points at the upstream `outputs/x`,
        # whatever order the nodes are packed in.
        self.homes = links.Homes(root)
        self.packed = [os.path.realpath(os.path.join(root, name)) for name in packed]
        self.stored: Dict[str, str] = {}
        self.inodes: Dict[Tuple[int, int], str] = {}

    def holds(self, real: str) -> bool:
        return any(real == top or real.startswith(top + os.sep) for top in self.packed)

    def add(self, name: str) -> None:
        self._add_dir(os.path.join(self.root, name), name)

    def _add_dir(self, path: str, arcname: str) -> None:
        import stat

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
            # Its own bytes, never a hard link: that would send the unmasked file.
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


def _framework_range(name: str) -> str:
    """SiliconCompiler's declared range for a framework distribution (cocotb's,
    in its `cocotb` extra), else the version installed here.

    A range, not a pin: the simulator and SiliconCompiler load the image's one copy.
    """
    from packaging.requirements import InvalidRequirement, Requirement

    for line in metadata.requires("siliconcompiler") or []:
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if canonical(requirement.name) == canonical(name) and str(requirement.specifier):
            return str(requirement.specifier)
    try:
        return _pin(metadata.version(name))
    except metadata.PackageNotFoundError:
        return ""


def _pin(version: str) -> str:
    """One installed version as the specifier the server resolves to an image.

    `==`, deliberately not `>=`: manifests read only backwards, and a newer
    image writes every returned manifest in the direction this one cannot read.
    A dev build asks by prefix: its commit-local segment matches no image.
    Spelled `==0.38.10.*`; `==0.38.10.dev*` is not legal PEP 440.
    """
    from packaging.version import InvalidVersion, Version

    try:
        parsed = Version(version)
    except InvalidVersion:
        return f"=={version}"

    if parsed.is_devrelease:
        return f"=={parsed.base_version}.*"
    return f"=={version}"


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


def _fitted(lead: str, items: List[str]) -> str:
    '''``lead`` and as many ``items`` as fit in `MAX_CANCEL_REASON`, then *and N
    more* (surface D288). One line: the server takes no control character.'''
    items = [" ".join(_UNPRINTABLE.sub(" ", str(item)).split()) for item in items]
    for count in range(len(items), 0, -1):
        rest = len(items) - count
        tail = f"; and {rest} more" if rest else ""
        text = lead + "; ".join(items[:count]) + tail
        if len(text) <= MAX_CANCEL_REASON:
            return text
    rest = len(items) - 1
    tail = f"; and {rest} more" if rest else ""
    room = MAX_CANCEL_REASON - len(lead) - len(tail) - 3
    return lead + items[0][:max(room, 0)] + "..." + tail


def _moved_at(node: Dict[str, Any]) -> Optional[float]:
    '''When a node reached its state: a finished node's finish, a running one's start.'''
    if node.get("terminal"):
        when = node.get("finished_at")
    elif node.get("state") == "running":
        when = node.get("started_at")
    else:
        return None
    return _epoch(when) if when else None


def _named(asked) -> str:
    '''`upload_sources` as a person reads it.'''
    return ", ".join(f"the dataroot {','.join(item.get('keypath') or ())}"
                     if item.get("kind") == "dataroot" else
                     f"the Python package {item.get('name')}"
                     for item in asked)
