'''
Starting the manifest's read (`manifestread`), and holding it to its limits.

🔴 The process starts with nothing of the server's (profile §5;
implementation-notes §E): an empty environment bar its own ``HOME``,
``TMPDIR`` and the ``PYTHONPATH`` of this server's SiliconCompiler, so no
credential, proxy or data-directory path; an empty working directory outside
the upload's tree, so the upload is never on ``sys.path``; no inherited
descriptor; and one request. It is killed at a wall-clock limit or when the job
leaves `staging`, and contains itself before opening anything.
'''

import functools
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


# The read's own directory in the job root, outside the extraction root.
READ_DIRNAME = "sc-server-read"

_POLL_SECONDS = 0.25

_TAIL_BYTES = 4000


class ReadFailed(Exception):
    '''The read did not produce a summary; ``timed_out`` where it ran past its time.'''

    def __init__(self, message: str, timed_out: bool = False):
        super().__init__(message)
        self.timed_out = timed_out


class Cancelled(Exception):
    '''The job left `staging` while its manifest was read.'''


def run_read(asked: Dict[str, Any], workdir, timeout: float,
             alive: Optional[Callable[[], bool]] = None,
             cpu_seconds: Optional[int] = None,
             memory_bytes: Optional[int] = None) -> Any:
    '''Run one read on this host; returns its summary, parsed, not yet validated.

    Raises :class:`ReadFailed`, :class:`Cancelled` once ``alive`` is false, or
    ``OSError`` for this server's own failure to start it.
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
    '''Run one read as a batch job in the job's own image (`images.read_bundle`, profile D63).'''
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
    '''Run one read in a container of the job's image: no network, only the tree, read-only.'''
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


def probe() -> Dict[str, bool]:
    '''What a read's containment achieves on this host, asked once of a real read process.'''
    return dict(_probe())


@functools.cache
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
    '''This server's interpreter, without user site or (3.11+) the cwd on its path.'''
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
           # The server's own install: a development checkout is on no default path.
           "PYTHONPATH": str(Path(siliconcompiler.__file__).resolve().parent.parent)}
    if cpu_seconds:
        env["SC_READ_CPU_SECONDS"] = str(int(cpu_seconds))
    if memory_bytes:
        env["SC_READ_MEMORY_BYTES"] = str(int(memory_bytes))
    return env


def _kill(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
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
