'''
Handing a job to whatever runs it: one batch job per run, its id kept in
``jobs.scheduler_job_id`` and polled. The id is just text; only this module
knows what it means.
'''

import logging
import os
import shlex
import signal
import subprocess
import sys

from pathlib import Path

__all__ = ["DispatchError", "Dispatcher", "LocalDispatcher", "SlurmDispatcher",
           "dispatcher_for"]


logger = logging.getLogger("sc-server")

# Scheduler commands run inside requests, so a wedged controller must not stall one.
COMMAND_TIMEOUT = 20

RUN_LOG = "sc-server-run.log"

_RUNNER = "siliconcompiler.remote.server.running.runner"


class DispatchError(RuntimeError):
    '''The job could not be handed over.'''


class Dispatcher:
    '''One way of starting a run and finding out whether it is still going.'''

    def submit(self, job_id: str, jobroot: Path, manifest: Path) -> str:
        raise NotImplementedError

    def is_alive(self, scheduler_job_id: str) -> bool:
        '''Whether the scheduler still has this job: a tie-breaker, since the
        run's progress file says what happened.'''
        raise NotImplementedError

    def cancel(self, scheduler_job_id: str, node_names=()) -> None:
        raise NotImplementedError


class LocalDispatcher(Dispatcher):
    '''Run it here, in a process of its own: ``-cluster local``.'''

    def __init__(self):
        # Kept so a finished child is reaped, not left a zombie that is alive for ever.
        self._children = {}

    def submit(self, job_id: str, jobroot: Path, manifest: Path) -> str:
        with open(jobroot / RUN_LOG, "ab") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", _RUNNER, str(manifest)],
                cwd=str(jobroot), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                # Its own session, so a cancel reaches the node processes too.
                start_new_session=True)

        self._children[process.pid] = process
        return f"local:{process.pid}"

    def is_alive(self, scheduler_job_id: str) -> bool:
        pid = int(scheduler_job_id.split(":", 1)[1])

        process = self._children.get(pid)
        if process is not None:
            return process.poll() is None

        # Started before a restart: the pid may have been reused, which
        # kill(pid, 0) cannot tell.
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                return _RUNNER.encode() in f.read()
        except OSError:
            return False

    def cancel(self, scheduler_job_id: str, node_names=()) -> None:
        try:
            os.killpg(int(scheduler_job_id.split(":", 1)[1]), signal.SIGTERM)
        except OSError as e:
            logger.debug(f"could not signal {scheduler_job_id}: {e}")


class SlurmDispatcher(Dispatcher):
    '''``sbatch`` it, and ask ``squeue`` about it. The batch job orchestrates:
    it submits each node as a job of its own.'''

    def submit(self, job_id: str, jobroot: Path, manifest: Path) -> str:
        script = jobroot / "sc-server-run.sh"
        script.write_text(
            "#!/bin/sh\n"
            f"exec {shlex.quote(sys.executable)} -m {_RUNNER} {shlex.quote(str(manifest))}\n")
        script.chmod(0o755)

        # --no-requeue: a requeue would rerun the runner over existing output.
        completed = _run(["sbatch", "--parsable", "--no-requeue", f"--job-name=sc-{job_id}",
                          f"--chdir={jobroot}", f"--output={jobroot / RUN_LOG}", str(script)])
        if completed.returncode != 0:
            raise DispatchError("sbatch refused this job: "
                                f"{completed.stderr.strip() or completed.stdout.strip()}")

        # --parsable prints "<jobid>" or "<jobid>;<cluster>".
        return completed.stdout.strip().split(";")[0]

    def is_alive(self, scheduler_job_id: str) -> bool:
        queued = _run(["squeue", "-h", "-j", scheduler_job_id, "-o", "%T"])
        if queued.returncode == 0 and queued.stdout.strip():
            return True

        # squeue forgets a job minutes after it ends; sacct remembers.
        finished = _run(["sacct", "-n", "-X", "-j", scheduler_job_id, "-o", "State"])
        states = {line.split()[0] for line in finished.stdout.splitlines() if line.strip()}
        if finished.returncode != 0 or not states:
            # Cannot tell, so never declare a running job lost.
            return True
        return bool(states & {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING",
                              "RESIZING", "SUSPENDED", "REQUEUED"})

    def cancel(self, scheduler_job_id: str, node_names=()) -> None:
        '''Stop the run and the node jobs it started, named
        ``<remoteid>_<step>_<index>`` by SiliconCompiler's Slurm scheduler.'''
        targets = [scheduler_job_id]
        if node_names:
            listed = _run(["squeue", "-h", "-o", "%i", "--name", ",".join(node_names)])
            targets = listed.stdout.split() + targets

        completed = _run(["scancel", *targets])
        if completed.returncode != 0:
            logger.warning(f"scancel {' '.join(targets)} failed: {completed.stderr.strip()}")


def dispatcher_for(cluster: str) -> Dispatcher:
    '''The dispatcher one deployment's ``-cluster`` names.'''
    return SlurmDispatcher() if cluster == "slurm" else LocalDispatcher()


def _run(command) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True,
                              timeout=COMMAND_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        logger.error(f"{command[0]} failed: {e}")
        return subprocess.CompletedProcess(command, 1, "", str(e))
