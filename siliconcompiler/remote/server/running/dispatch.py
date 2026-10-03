'''
Handing a job to whatever runs it.

One batch job per run, its id in ``jobs.scheduler_job_id`` and polled, never
a blocking ``srun`` per node held open by the API process, which would make it
a Slurm submit host. ``slurmrestd`` submits batch jobs only, so a REST
transport is a swap: the id is just text, and only this module knows what it
means.
'''

import logging
import os
import shlex
import shutil
import signal
import subprocess
import sys

from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = ["dispatcher_for", "Dispatcher", "LocalDispatcher", "SlurmDispatcher",
           "DispatchError"]


logger = logging.getLogger("sc-server")

# Scheduler commands run inside requests, so a wedged controller must not stall one.
COMMAND_TIMEOUT = 20

RUN_SCRIPT = "sc-server-run.sh"
RUN_LOG = "sc-server-run.log"
BUILD_SCRIPT = "sc-server-build.sh"
READ_SCRIPT = "sc-server-read.sh"


class DispatchError(RuntimeError):
    '''The job could not be handed over.'''


class Dispatcher:
    '''One way of starting a run and finding out whether it is still going.'''

    name = "none"

    def submit(self, job_id: str, jobroot: Path, manifest: Path,
               image: Optional[str] = None, queue: Optional[str] = None) -> str:
        raise NotImplementedError

    def is_alive(self, scheduler_job_id: str) -> bool:
        '''Whether the scheduler still has this job.

        Only a tie-breaker: the run's progress file says what happened.
        '''
        raise NotImplementedError

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        raise NotImplementedError

    def submit_build(self, name: str, workspace: Path, spec: Path,
                     queue: Optional[str] = None) -> str:
        '''Start one environment build (`envbuild`) into ``workspace``; returns its id.'''
        raise NotImplementedError

    def submit_read(self, name: str, workdir: Path, command: List[str], bundle: str,
                    timeout: int, queue: Optional[str] = None) -> str:
        '''Start one manifest read (`manifestread`) in ``bundle``; returns its id.

        It writes ``workdir``/summary.json. Only where jobs run in bundles.'''
        raise NotImplementedError

    def node_jobs(self, job_id: str, nodes) -> Dict[Tuple[str, str], str]:
        '''The scheduler's own id for each node of this job, where a node is a scheduler job.'''
        return {}

    def running_nodes(self, job_id: str, nodes) -> List[str]:
        '''The node jobs the scheduler still has.'''
        return []

    def describe(self, scheduler_job_id: str) -> Optional[str]:
        '''What the scheduler says of one of its jobs, for `diagnostics`, or None.'''
        return None


class LocalDispatcher(Dispatcher):
    '''Run it here, in a process of its own: ``-cluster local``, not a test double.'''

    name = "local"

    def __init__(self):
        # Kept so a finished child is reaped, not left a zombie that is alive forever.
        self._children: Dict[int, subprocess.Popen] = {}

    def submit(self, job_id: str, jobroot: Path, manifest: Path,
               image: Optional[str] = None, queue: Optional[str] = None) -> str:
        log = open(jobroot / RUN_LOG, "ab")
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "siliconcompiler.remote.server.running.runner",
                 str(manifest)],
                cwd=str(jobroot), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                # Its own session, so it survives the server and its Ctrl-C.
                start_new_session=True)
        finally:
            log.close()

        self._children[process.pid] = process
        return f"local:{process.pid}"

    def submit_build(self, name: str, workspace: Path, spec: Path,
                     queue: Optional[str] = None) -> str:
        from siliconcompiler.remote.server.packages.envbuild import LOG

        log = open(workspace / LOG, "ab")
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "siliconcompiler.remote.server.packages.envbuild",
                 str(spec)],
                cwd=str(workspace), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        finally:
            log.close()

        self._children[process.pid] = process
        return f"local:{process.pid}"

    def is_alive(self, scheduler_job_id: str) -> bool:
        pid = _local_pid(scheduler_job_id)
        if pid is None:
            return False

        process = self._children.get(pid)
        if process is not None:
            return process.poll() is None

        # Started before a restart: check the command line in /proc, since the
        # pid may have been reused and kill(pid, 0) cannot tell.
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                command = f.read()
            return any(module in command for module in (
                b"siliconcompiler.remote.server.running.runner",
                b"siliconcompiler.remote.server.packages.envbuild"))
        except OSError:
            return False

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        pid = _local_pid(scheduler_job_id)
        if pid is None:
            return
        try:
            # The whole session, so the forked node processes stop too.
            os.killpg(pid, signal.SIGTERM)
        except OSError as e:
            logger.debug(f"could not signal {scheduler_job_id}: {e}")


class SlurmDispatcher(Dispatcher):
    '''``sbatch`` it, and ask ``squeue`` about it.

    Scripts go in the job's directory, not ``--wrap``, so what ran is readable.
    '''

    name = "slurm"

    def submit(self, job_id: str, jobroot: Path, manifest: Path,
               image: Optional[str] = None, queue: Optional[str] = None) -> str:
        script = jobroot / RUN_SCRIPT
        script.write_text(
            "#!/bin/sh\n"
            "# Written by sc-server. This batch job is the run's ORCHESTRATOR:\n"
            "# it loads the manifest, drives SiliconCompiler's scheduler and\n"
            "# writes the progress file. Each node is submitted from here as a\n"
            "# job of its own, so this process holds one core and uses almost\n"
            "# none of it.\n"
            f"exec {shlex.quote(sys.executable)} "
            "-m siliconcompiler.remote.server.running.runner "
            f"{shlex.quote(str(manifest))}\n")
        script.chmod(0o755)

        command = [
            "sbatch", "--parsable",
            # A requeue would rerun the runner over existing output, maybe
            # after the job was declared lost. One dispatch, one outcome.
            "--no-requeue",
            f"--job-name=sc-{job_id}",
            f"--chdir={jobroot}",
            f"--output={jobroot / RUN_LOG}",
        ]

        if queue:
            # Its own partition: it coordinates, and would idle in a compute slot.
            command.append(f"--partition={queue}")

        if image:
            # The framework image, so the manifest is interpreted by the
            # SiliconCompiler the job asked for. It submits every node, so it
            # needs the Slurm client, slurm.conf and the munge socket.
            command.append(f"--container={image}")

        command.append(str(script))

        completed = _run(command)

        if completed.returncode != 0:
            raise DispatchError(
                f"sbatch refused this job: {completed.stderr.strip() or completed.stdout.strip()}")

        # --parsable prints "<jobid>" or "<jobid>;<cluster>".
        return completed.stdout.strip().split(";")[0]

    def submit_build(self, name: str, workspace: Path, spec: Path,
                     queue: Optional[str] = None) -> str:
        '''``sbatch`` one environment build onto a compute node.

        On the host, no ``--container``: the build starts its own isolated
        container and runs the proxy it reaches out through.
        '''
        from siliconcompiler.remote.server.packages.envbuild import LOG

        script = workspace / BUILD_SCRIPT
        script.write_text(
            "#!/bin/sh\n"
            "# Written by sc-server: a job's Python packages, built into an\n"
            "# image. It writes result.json beside this file.\n"
            f"exec {shlex.quote(sys.executable)} "
            "-m siliconcompiler.remote.server.packages.envbuild "
            f"{shlex.quote(str(spec))}\n")
        script.chmod(0o755)

        command = ["sbatch", "--parsable", "--no-requeue", "--ntasks=1",
                   f"--job-name=sc-envbuild-{name}", f"--chdir={workspace}",
                   f"--output={workspace / LOG}"]
        if queue:
            # So a burst of builds waits here, not in the node slots flows use.
            command.append(f"--partition={queue}")
        command.append(str(script))

        completed = _run(command)
        if completed.returncode != 0:
            raise DispatchError(
                f"sbatch refused the build: {completed.stderr.strip() or completed.stdout.strip()}")
        return completed.stdout.strip().split(";")[0]

    def submit_read(self, name: str, workdir: Path, command: List[str], bundle: str,
                    timeout: int, queue: Optional[str] = None) -> str:
        '''``sbatch`` one manifest read into the job's own image.

        Nothing of this process's goes with it: ``--export=NONE``, and the
        bundle mounts only the extracted tree, read-only, with no network
        (`images.read_bundle`). The summary comes back on stdout.
        '''
        script = workdir / READ_SCRIPT
        script.write_text(
            "#!/bin/sh\n"
            "# Written by sc-server: one job's manifest, read in its own image.\n"
            "export HOME=/tmp TMPDIR=/tmp LC_ALL=C.UTF-8 PYTHONNOUSERSITE=1\n"
            "cd /tmp\n"
            f"exec {' '.join(shlex.quote(part) for part in command)}\n")
        script.chmod(0o755)

        submitted = ["sbatch", "--parsable", "--no-requeue", "--ntasks=1", "--export=NONE",
                     f"--job-name=sc-read-{name}", "--chdir=/tmp",
                     f"--time={max(1, -(-int(timeout) // 60))}",
                     f"--output={workdir / 'summary.json'}",
                     f"--error={workdir / 'stderr.txt'}",
                     f"--container={bundle}"]
        if queue:
            submitted.append(f"--partition={queue}")
        submitted.append(str(script))

        completed = _run(submitted)
        if completed.returncode != 0:
            raise DispatchError(f"sbatch refused the manifest's read: "
                                f"{completed.stderr.strip() or completed.stdout.strip()}")
        return completed.stdout.strip().split(";")[0]

    def is_alive(self, scheduler_job_id: str) -> bool:
        queued = _run(["squeue", "-h", "-j", scheduler_job_id, "-o", "%T"])
        if queued.returncode == 0 and queued.stdout.strip():
            return True

        # squeue forgets a job minutes after it ends; sacct remembers.
        finished = _run(["sacct", "-n", "-X", "-j", scheduler_job_id, "-o", "State"])
        if finished.returncode != 0:
            # No accounting: cannot tell, so never declare a running job lost.
            return True

        states = {line.strip().split()[0] for line in finished.stdout.splitlines()
                  if line.strip()}
        if not states:
            return True
        return bool(states & {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING",
                              "RESIZING", "SUSPENDED", "REQUEUED"})

    def describe(self, scheduler_job_id: str) -> Optional[str]:
        '''`sacct` and `scontrol show job` for one job, whole.'''
        said = []
        for command in (["sacct", "-j", scheduler_job_id, "--parsable2",
                         "--format=JobID,JobName,Partition,State,ExitCode,Start,End,"
                         "Elapsed,NodeList,MaxRSS,Reason"],
                        ["scontrol", "show", "job", scheduler_job_id]):
            done = _run(command)
            said.append(f"$ {' '.join(command)}\n{done.stdout}{done.stderr}")
        return "\n".join(said)

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        '''Stop the run, and the node jobs it started, named rather than left to Slurm.

        One ``scancel``, node ids first, so the work stops before its coordinator.
        '''
        targets = [str(node_id) for node_id in node_job_ids if node_id]
        if scheduler_job_id:
            # Falsy when only orphans are reaped: scancel on a finished job errors.
            targets.append(scheduler_job_id)

        if not targets:
            return

        completed = _run(["scancel", *targets])
        if completed.returncode != 0:
            logger.warning(
                f"scancel {' '.join(targets)} failed: {completed.stderr.strip()}")

    def node_jobs(self, job_id: str, nodes) -> Dict[Tuple[str, str], str]:
        '''Which Slurm job each node became, by the name the server can derive.

        ``SlurmSchedulerNode.get_job_name`` spells it ``<remoteid>_<step>_<index>``.
        '''
        return self._by_name(job_id, nodes, remembered=True)

    def running_nodes(self, job_id: str, nodes) -> List[str]:
        '''The node jobs the scheduler still has, as ids: a finished one is never scancelled.'''
        return list(self._by_name(job_id, nodes, remembered=False).values())

    def _by_name(self, job_id: str, nodes, remembered: bool):
        '''Look node jobs up by name: `squeue`, then `sacct` for the rest if ``remembered``.'''
        wanted = {f"{job_id}_{step}_{index}": (step, index) for step, index in nodes}
        if not wanted:
            return {}

        names = ",".join(wanted)
        commands = [["squeue", "-h", "-o", "%i %j", "--name", names]]
        if remembered:
            commands.append(["sacct", "-n", "-X", "--name", names,
                             "-o", "JobID,JobName%128"])

        found: Dict[Tuple[str, str], str] = {}

        for command in commands:
            if len(found) == len(wanted):
                break

            completed = _run(command)
            if completed.returncode != 0:
                # A missing id is a gap in the record, not a failed request.
                continue

            for line in completed.stdout.splitlines():
                parts = line.split()
                if len(parts) != 2:
                    continue
                scheduler_id, name = parts
                node = wanted.get(name)
                if node is not None and node not in found:
                    found[node] = scheduler_id

        return found


def dispatcher_for(cluster: str) -> Dispatcher:
    '''The dispatcher one deployment's ``-cluster`` names.'''
    if cluster == "local":
        return LocalDispatcher()
    if cluster == "slurm":
        if not shutil.which("sbatch"):
            raise DispatchError(
                "-cluster slurm was requested and sbatch is not on PATH: this "
                "server has to be able to submit to the cluster it names")
        return SlurmDispatcher()
    raise DispatchError(f"unknown cluster: {cluster}")


def _local_pid(scheduler_job_id: str) -> Optional[int]:
    if not scheduler_job_id or not scheduler_job_id.startswith("local:"):
        return None
    try:
        return int(scheduler_job_id.split(":", 1)[1])
    except ValueError:                                          # pragma: no cover
        return None


def _run(command) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True,
                              timeout=COMMAND_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"{command[0]} failed: {e}")
        return subprocess.CompletedProcess(command, 1, "", str(e))
