'''
Handing a job to whatever runs it.

🔴 **The job is the unit of submission.** One batch job per run, its id recorded
in ``jobs.scheduler_job_id``, polled once per run. That is a deliberate change
from the shape this replaces -- a blocking ``srun`` per node, held open by the
API process for the length of the run -- and it is what makes the API process
something other than a Slurm submit host.

✅ **It is also what makes a REST transport a swap rather than a rewrite.**
``slurmrestd`` submits *batch* jobs only: ``POST /slurm/vX/job/submit`` is the
``sbatch`` equivalent and there is no ``srun`` over REST. So ``sbatch`` and REST
are one design with two transports, and the seam that matters is not a base
class with one implementation -- it is that ``jobs.scheduler_job_id`` is just
text and that this is the only module which knows what it means.
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

# Bounds on the scheduler commands. A wedged controller must not stall a request
# handler: every one of these runs while somebody is waiting on an HTTP
# response.
COMMAND_TIMEOUT = 20

RUN_SCRIPT = "sc-server-run.sh"
RUN_LOG = "sc-server-run.log"


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

        Only ever consulted as a tie-breaker. The run's own progress file is
        what says what happened; this answers the different question of whether
        anything is still there to write one.
        '''
        raise NotImplementedError

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        raise NotImplementedError

    def node_jobs(self, job_id: str, nodes) -> Dict[Tuple[str, str], str]:
        '''The scheduler's own id for each node of this job, where it has one.

        🔴 Only meaningful where a node IS a scheduler job. On a deployment that
        runs the whole flow in one process the nodes are processes inside it,
        and an empty answer is the truthful one rather than a gap -- which is
        why `job_nodes.scheduler_job_id` is nullable.
        '''
        return {}

    def running_nodes(self, job_id: str, nodes) -> List[str]:
        '''The node jobs the scheduler still has. Nothing, where nodes are not
        scheduler jobs.'''
        return []


class LocalDispatcher(Dispatcher):
    '''Run it here, in a process of its own.

    Not a test double: a single-machine deployment with no cluster is an
    ordinary way to run this server, and it is what ``-cluster local`` means.
    '''

    name = "local"

    def __init__(self):
        # Kept so a finished child is reaped rather than left a zombie, which
        # would answer `is_alive` forever. Lost across a restart, which is what
        # the /proc fallback below is for.
        self._children: Dict[int, subprocess.Popen] = {}

    def submit(self, job_id: str, jobroot: Path, manifest: Path,
               image: Optional[str] = None, queue: Optional[str] = None) -> str:
        log = open(jobroot / RUN_LOG, "ab")
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "siliconcompiler.remote.server.runner",
                 str(manifest)],
                cwd=str(jobroot), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                # Its own session, so the run does not die with the server and
                # is not signalled by a Ctrl-C meant for the console.
                start_new_session=True)
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

        # Started before this process was, so there is nothing to reap and the
        # question is only whether the pid is still there. Read rather than
        # signalled: after a restart the run is not our child, and a pid can
        # have been reused by then -- /proc carries the command line, which a
        # bare kill(pid, 0) does not.
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                return b"siliconcompiler.remote.server.runner" in f.read()
        except OSError:
            return False

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        # `node_job_ids` is empty here by construction: nodes are processes in
        # the run's own tree, and the process group below covers them.
        pid = _local_pid(scheduler_job_id)
        if pid is None:
            return
        try:
            # The whole session: the run forks node processes, and signalling
            # only the parent leaves them running with nothing to report them.
            os.killpg(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError) as e:
            logger.debug(f"could not signal {scheduler_job_id}: {e}")


class SlurmDispatcher(Dispatcher):
    '''``sbatch`` it, and ask ``squeue`` about it.

    The script is written into the job's own directory rather than passed with
    ``--wrap``, so what was submitted is readable next to what it produced.
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
            "-m siliconcompiler.remote.server.runner "
            f"{shlex.quote(str(manifest))}\n")
        script.chmod(0o755)

        command = [
            "sbatch", "--parsable",
            # 🔴 A node failure ends this run; it does not silently start it
            # again. Slurm's default is to requeue, and a requeued batch job
            # re-executes the runner from the top -- against a build directory
            # that already has output in it, and quite possibly after this
            # server has already declared the job lost and told its owner so.
            # One dispatch, one outcome, and a resubmit is the owner's to make.
            "--no-requeue",
            f"--job-name=sc-{job_id}",
            f"--chdir={jobroot}",
            f"--output={jobroot / RUN_LOG}",
        ]

        if queue:
            # A partition of its own, because this process coordinates rather
            # than computes. On a compute partition it is a node slot held for
            # the length of the flow doing nothing.
            command.append(f"--partition={queue}")

        if image:
            # 🔴 The framework image, and this is what makes version matching
            # real rather than half-done: the process that INTERPRETS the
            # manifest is then the SiliconCompiler the job asked for, not
            # whichever one this cluster happens to have installed.
            #
            # ⚠️ Which puts a requirement on that image: it submits every node,
            # so it needs the Slurm client, slurm.conf and the munge socket
            # inside it. An image that has SiliconCompiler and no srun cannot
            # be a framework image on a cluster.
            command.append(f"--container={image}")

        command.append(str(script))

        completed = _run(command)

        if completed.returncode != 0:
            raise DispatchError(
                f"sbatch refused this job: {completed.stderr.strip() or completed.stdout.strip()}")

        # --parsable prints "<jobid>" or "<jobid>;<cluster>".
        return completed.stdout.strip().split(";")[0]

    def is_alive(self, scheduler_job_id: str) -> bool:
        queued = _run(["squeue", "-h", "-j", scheduler_job_id, "-o", "%T"])
        if queued.returncode == 0 and queued.stdout.strip():
            return True

        # squeue forgets a job minutes after it ends, so an empty answer is not
        # yet evidence: it means "not running now", which is also true of a job
        # that finished thirty seconds ago and whose progress file is about to
        # be read. sacct is the one that remembers.
        finished = _run(["sacct", "-n", "-X", "-j", scheduler_job_id, "-o", "State"])
        if finished.returncode != 0:
            # No accounting configured: the honest answer is "cannot tell", and
            # the safe direction is to believe the job is still there rather
            # than to declare a running job lost.
            return True

        states = {line.strip().split()[0] for line in finished.stdout.splitlines()
                  if line.strip()}
        if not states:
            return True
        return bool(states & {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING",
                              "RESIZING", "SUSPENDED", "REQUEUED"})

    def cancel(self, scheduler_job_id: str, node_job_ids=()) -> None:
        '''Stop the run, and stop the work it started.

        🔴 The nodes are jobs of their own now, so cancelling the orchestrator
        alone leaves them to Slurm's own cleanup -- which usually does end them,
        because a job dies with the ``srun`` that allocated it, but "usually"
        is not what a cancel should rest on when the alternative is naming them.

        Node ids first in the one call, so the work stops before the process
        coordinating it does. One call rather than one per node: a cancel is
        rare and user-initiated, and it should still not be N requests into
        slurmctld.
        '''
        targets = [str(node_id) for node_id in node_job_ids if node_id]
        if scheduler_job_id:
            # Falsy when the run is already gone and only its orphans are being
            # reaped: scancel on a job that has finished answers with an error,
            # and a warning per cancelled job would train an operator to ignore
            # them.
            targets.append(scheduler_job_id)

        if not targets:
            return

        completed = _run(["scancel", *targets])
        if completed.returncode != 0:
            logger.warning(
                f"scancel {' '.join(targets)} failed: {completed.stderr.strip()}")

    def node_jobs(self, job_id: str, nodes) -> Dict[Tuple[str, str], str]:
        '''Which Slurm job each node became.

        Addressed by NAME, because the name is derived from this server's own
        job id -- ``SlurmSchedulerNode.get_job_name`` spells it
        ``<remoteid>_<step>_<index>`` -- so nothing has to be passed back from
        the compute node to know what to ask for.

        ⚠️ Two queries and not one per node. ``squeue`` answers for the jobs
        that still exist, which is what a cancel needs; ``sacct`` is asked only
        for whatever is left, which is what the record needs after a node has
        finished and squeue has forgotten it.
        '''
        return self._by_name(job_id, nodes, remembered=True)

    def running_nodes(self, job_id: str, nodes) -> List[str]:
        '''The node jobs the scheduler still has, as ids.

        🔴 Still has, which is the whole difference from `node_jobs`. This is
        what a reaper needs: a job that already finished must not be scancelled,
        because scancel answers an error for it and a warning per finished node
        would train an operator to ignore them.
        '''
        return list(self._by_name(job_id, nodes, remembered=False).values())

    def _by_name(self, job_id: str, nodes, remembered: bool):
        '''Look node jobs up by the name the server can derive for them.

        ⚠️ Two queries and not one per node. `squeue` answers for the jobs that
        still exist; `sacct` is asked only for whatever is left, and only when
        a caller wants the ones it has forgotten.
        '''
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
                # No accounting configured, or a wedged controller. A missing id
                # is a gap in the record, not a reason to fail the request that
                # happened to be reconciling this job.
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
