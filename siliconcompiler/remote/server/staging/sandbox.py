'''
Starting the manifest's read, and holding it to its limits.

The read itself is `manifestread`. This is the server's side of it: a process
started from this server's own SiliconCompiler with nothing of the server's in
it, given one request, killed at a wall-clock limit or when the job leaves
`staging`, and read back bounded.

🔴 **What the process starts with** (profile §5; implementation-notes §E):

- an empty environment: its own ``HOME`` and ``TMPDIR``, and the one
  ``PYTHONPATH`` entry that finds this server's own SiliconCompiler, so none of
  the server's variables -- no credential, no proxy, no path to the data
  directory -- reaches it;
- a working directory of its own, empty, in the job root and outside the tree
  the upload expanded into, so the upload is never on its ``sys.path``;
- no inherited descriptor and ``stdin`` closed;
- one request naming the extracted tree, and nothing else of the server's.

It then contains itself (`manifestread.contain`) before it opens anything:
network and user namespaces where the kernel lets it, and its own CPU, memory
and file-size limits.
'''

import json
import os
import shutil
import signal
import subprocess
import sys
import time

from pathlib import Path
from typing import Any, Callable, Dict, Optional

__all__ = ["ReadFailed", "Cancelled", "run_read", "run_read_in_bundle",
           "run_read_in_image", "probe", "READ_DIRNAME"]


# The read's own directory in the job root, beside the progress file and
# outside the extraction root: its request, its output, its HOME.
READ_DIRNAME = "sc-server-read"

# How often a running read is looked at: its exit, the clock, and the job.
_POLL_SECONDS = 0.25

# What of a failed read's stderr is kept for the server's log.
_TAIL_BYTES = 4000


class ReadFailed(Exception):
    '''The read did not produce a summary. ``timed_out`` where it ran past the
    time it was given, which may be what was left of the job's staging.'''

    def __init__(self, message: str, timed_out: bool = False):
        super().__init__(message)
        self.timed_out = timed_out


class Cancelled(Exception):
    '''The job left `staging` while its manifest was read.'''


def run_read(asked: Dict[str, Any], workdir, timeout: float,
             alive: Optional[Callable[[], bool]] = None,
             cpu_seconds: Optional[int] = None,
             memory_bytes: Optional[int] = None) -> Any:
    '''Run one read on this host; its summary, parsed, not yet validated.

    Raises :class:`ReadFailed` for a read that ran past its limits or
    returned nothing parseable, :class:`Cancelled` where ``alive`` stopped
    answering true, and ``OSError`` where the process could not be started --
    this server's own failure, not the manifest's.
    '''
    workdir = _fresh(workdir)
    home = workdir / "home"
    home.mkdir(parents=True)
    (workdir / "request.json").write_text(json.dumps(asked))
    stdout_path, stderr_path = workdir / "summary.json", workdir / "stderr.txt"

    with open(stdout_path, "wb") as out, open(stderr_path, "wb") as err:
        process = subprocess.Popen(
            _command(workdir / "request.json"), env=_environment(home, cpu_seconds,
                                                                 memory_bytes),
            cwd=str(home), stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            close_fds=True, start_new_session=True)

    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            if time.monotonic() >= deadline:
                _kill(process)
                raise ReadFailed(f"the manifest's read ran past its {int(timeout)}s limit",
                                 timed_out=True)
            if alive is not None and not alive():
                _kill(process)
                raise Cancelled()
            time.sleep(_POLL_SECONDS)
    finally:
        if process.poll() is None:
            _kill(process)

    if process.returncode != 0:
        tail = _tail(stderr_path)
        why = _signal_name(process.returncode)
        raise ReadFailed(f"the manifest's read ended {why}" + (f": {tail}" if tail else ""))
    return _summary_in(stdout_path, stderr_path)


def run_read_in_bundle(dispatcher, asked: Dict[str, Any], workdir, bundle: str,
                       timeout: float, alive: Optional[Callable[[], bool]] = None,
                       queue: Optional[str] = None, cpu_seconds: Optional[int] = None,
                       memory_bytes: Optional[int] = None) -> Any:
    '''Run one read in the job's own image, as a batch job of its own in a
    bundle made by `images.read_bundle` (profile D63: in the job's container
    where containers are configured). As :func:`run_read` answers.'''
    workdir = _fresh(workdir)
    command = [*_python(), "-m", "siliconcompiler.remote.server.staging.manifestread",
               json.dumps(asked)]
    limits = [f"SC_READ_CPU_SECONDS={int(cpu_seconds)}"] if cpu_seconds else []
    limits += [f"SC_READ_MEMORY_BYTES={int(memory_bytes)}"] if memory_bytes else []
    if limits:
        command = ["env", *limits, *command]
    read_id = dispatcher.submit_read(Path(asked["tree"]).parents[1].name[:12] or "job",
                                     workdir, command, bundle, int(timeout), queue=queue)

    deadline = time.monotonic() + timeout
    while dispatcher.is_alive(read_id):
        if time.monotonic() >= deadline:
            dispatcher.cancel(read_id)
            raise ReadFailed(f"the manifest's read ran past its {int(timeout)}s limit",
                             timed_out=True)
        if alive is not None and not alive():
            dispatcher.cancel(read_id)
            raise Cancelled()
        time.sleep(1)
    return _summary_in(workdir / "summary.json", workdir / "stderr.txt")


def run_read_in_image(asked: Dict[str, Any], workdir, image: str, timeout: float,
                      alive: Optional[Callable[[], bool]] = None,
                      cpu_seconds: Optional[int] = None,
                      memory_bytes: Optional[int] = None) -> Any:
    '''Run one read in the job's own image, as a container of its own: no
    network, and the job's extracted tree, read-only, the only thing mounted.
    As :func:`run_read` answers; ``OSError`` where the image cannot be had.'''
    import docker
    import docker.errors

    workdir = _fresh(workdir)
    tree = str(asked["tree"])
    environment = {"HOME": "/tmp", "TMPDIR": "/tmp", "LC_ALL": "C.UTF-8",
                   "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    if cpu_seconds:
        environment["SC_READ_CPU_SECONDS"] = str(int(cpu_seconds))
    if memory_bytes:
        environment["SC_READ_MEMORY_BYTES"] = str(int(memory_bytes))

    try:
        client = docker.from_env()
        container = client.containers.run(
            image, ["python3", "-s", "-B", "-m",
                    "siliconcompiler.remote.server.staging.manifestread", json.dumps(asked)],
            detach=True, network_mode="none", environment=environment,
            working_dir="/tmp", tmpfs={"/tmp": "size=256m"}, read_only=True,
            volumes={tree: {"bind": tree, "mode": "ro"}},
            mem_limit=int(memory_bytes) if memory_bytes else None,
            user=f"{os.getuid()}:{os.getgid()}")
    except docker.errors.DockerException as e:
        raise OSError(f"the image the manifest is read in could not be started: {e}") \
            from None

    deadline = time.monotonic() + timeout
    try:
        while True:
            container.reload()
            if container.status in ("exited", "dead"):
                break
            if time.monotonic() >= deadline:
                raise ReadFailed(f"the manifest's read ran past its {int(timeout)}s limit",
                                 timed_out=True)
            if alive is not None and not alive():
                raise Cancelled()
            time.sleep(_POLL_SECONDS)
        code = container.attrs.get("State", {}).get("ExitCode")
        (workdir / "summary.json").write_bytes(container.logs(stdout=True, stderr=False))
        (workdir / "stderr.txt").write_bytes(container.logs(stdout=False, stderr=True))
    finally:
        try:
            container.remove(force=True)
        except docker.errors.DockerException:
            pass
    if code:
        tail = _tail(workdir / "stderr.txt")
        raise ReadFailed(f"the manifest's read ended with exit status {code}"
                         + (f": {tail}" if tail else ""))
    return _summary_in(workdir / "summary.json", workdir / "stderr.txt")


def _fresh(workdir) -> Path:
    workdir = Path(workdir)
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    return workdir


def _summary_in(stdout_path: Path, stderr_path: Path) -> Any:
    '''The summary a finished read wrote, bounded; ReadFailed without one.'''
    from siliconcompiler.remote.server.staging.manifestread import MAX_SUMMARY_BYTES

    try:
        with open(stdout_path, "rb") as f:
            body = f.read(MAX_SUMMARY_BYTES + 1)
    except OSError:
        body = b""
    if len(body) > MAX_SUMMARY_BYTES:
        raise ReadFailed(f"the manifest's read said more than {MAX_SUMMARY_BYTES} bytes")
    try:
        return json.loads(body)
    except ValueError:
        tail = _tail(stderr_path)
        raise ReadFailed("the manifest's read returned no summary"
                         + (f": {tail}" if tail else "")) from None


_probed: Optional[Dict[str, bool]] = None


def probe() -> Dict[str, bool]:
    '''What a read's containment achieves on this host: a real read's
    process, with an empty request, asked only to contain itself. Once per
    process.'''
    global _probed
    if _probed is None:
        _probed = _probe()
    return dict(_probed)


def _probe() -> Dict[str, bool]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="sc-server-probe-") as home:
        try:
            result = subprocess.run(
                [*_python(), "-c",
                 "import json, sys; "
                 "from siliconcompiler.remote.server.staging.manifestread import contain; "
                 "sys.stdout.write(json.dumps(contain()))"],
                env=_environment(Path(home)), cwd=home, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, close_fds=True)
            return json.loads(result.stdout or b"{}")
        except (OSError, ValueError, subprocess.SubprocessError):
            return {"network": False, "limits": False}


def _python():
    '''This server's own interpreter, isolated from its user site, and --
    where Python can -- from the working directory as a path entry.'''
    flags = ["-s", "-B"]
    if sys.version_info >= (3, 11):
        flags.append("-P")
    return [sys.executable, *flags]


def _command(request: Path):
    return [*_python(), "-m", "siliconcompiler.remote.server.staging.manifestread", f"@{request}"]


def _environment(home: Path, cpu_seconds: Optional[int] = None,
                 memory_bytes: Optional[int] = None) -> Dict[str, str]:
    '''🔴 Nothing of the server's: its own HOME, and where this server's
    SiliconCompiler is.'''
    import siliconcompiler

    env = {"HOME": str(home), "TMPDIR": str(home), "LC_ALL": "C.UTF-8",
           "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           # The server's own install, which is not the job's: a development
           # checkout is on no default path.
           "PYTHONPATH": str(Path(siliconcompiler.__file__).resolve().parent.parent)}
    if cpu_seconds:
        env["SC_READ_CPU_SECONDS"] = str(int(cpu_seconds))
    if memory_bytes:
        env["SC_READ_MEMORY_BYTES"] = str(int(memory_bytes))
    return env


def _kill(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def _signal_name(code: int) -> str:
    if code < 0:
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = f"signal {-code}"
        # A CPU limit is SIGXCPU, and a memory limit usually a MemoryError or
        # a SIGKILL from the kernel.
        return f"on {name}"
    return f"with exit status {code}"


def _tail(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - _TAIL_BYTES))
            text = f.read().decode("utf-8", "replace").strip()
    except OSError:
        return ""
    return text.splitlines()[-1] if text else ""
