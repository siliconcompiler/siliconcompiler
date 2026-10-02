'''
The server's own copies of remote sources: held, and fetched only from the
allowlist.

A job's remote dataroot -- lambdapdk's PDKs are the common case -- is supplied
by (source, ref), never by a path the job names. This module holds those
copies under ``<datadir>/sources/`` and fetches the ones it does not hold.

🔴 **The run never fetches.** The run points a supplied dataroot at the held
copy, from what the server wrote beside its manifest
(`runspec.point_dataroots`), so nothing in the run reaches the network on a
job's behalf. What does is here, and it is SiliconCompiler's own resolver -- so
the server's copy is the user's, submodules and LFS objects included (surface
D164) -- run unchanged in a process of its own (`staging.fetch`), which has no
credential to send and one way out: a proxy admitting the allowlist's hosts,
never a non-public address, and at most `MAX_SOURCE_BYTES`. The source a job
names is checked against the allowlist, path and all, before it starts.

A submodule or LFS store off the allowlist fails the fetch for good, which
sends the source to the ask loop like any other the server cannot fetch.

⚠️ **Failures are two kinds, and the difference decides what the job does.** A
transient one -- ``429``, a ``5xx``, a timeout -- is retried until the job's
deadline, or a GitHub blip becomes a multi-gigabyte upload. A permanent one --
``401``, ``403``, ``404`` -- sends the job back to ask the client, which has
the credentials the server does not: GitHub answers ``404`` for a private
repository it will not show.
'''

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time

from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlsplit

from siliconcompiler.remote.server.staging import allowlist

__all__ = ["SourceStore", "Transient", "Permanent", "download_url"]


logger = logging.getLogger("sc-server")

# The most one source may weigh, downloaded. A PDK is gigabytes; this is a
# ceiling on a mistake, not a budget.
MAX_SOURCE_BYTES = 16 * 1024 ** 3

# How long a copy of a moving ref -- a branch -- stands for that ref: one
# job's staging, never the next job's.
MOVING_HOLD_SECONDS = 3600

_COMPLETE = ".complete"
_CURRENT = "current"


class Transient(Exception):
    '''A fetch that may work if tried again.'''


class Permanent(Exception):
    '''A fetch that will not work from here: the client must send it.'''


def download_url(source: str, ref: Optional[str]) -> str:
    '''The URL SiliconCompiler's https resolver would fetch for this source --
    ``<source><ref>.tar.gz`` for a source ending in ``/``.'''
    if source.endswith("/") and ref:
        return f"{source}{ref}.tar.gz"
    return source


class SourceStore:
    '''Held copies, by (source, ref), under ``<datadir>/sources/``.'''

    def __init__(self, datadir, rules: Sequence[allowlist.Rule]):
        self.root = Path(datadir) / "sources"
        self.rules = list(rules)

    def _key(self, source: str, ref: Optional[str]) -> Path:
        digest = hashlib.sha256(f"{source}\0{ref or ''}".encode()).hexdigest()
        return self.root / digest[:32]

    def held(self, source: Optional[str], ref: Optional[str]) -> Optional[str]:
        '''The held copy's root, or None where this server has not got it --
        or holds it for a moving ref, fetched longer ago than one job stages.'''
        if not source:
            return None
        where = self._key(source, ref)
        try:
            copy = where / (where / _CURRENT).read_text().strip()
        except OSError:
            return None
        try:
            marker = json.loads((copy / _COMPLETE).read_text())
        except (OSError, ValueError):
            return None
        if marker.get("moving") and \
                time.time() - marker.get("fetched_at", 0) > MOVING_HOLD_SECONDS:
            return None
        return str(copy / "data")

    def allowlisted(self, source: Optional[str], ref: Optional[str]) -> bool:
        '''Whether this server would fetch the source itself.

        🔴 Never one whose URL has a query (surface D308): its values are
        masked, so it is asked for -- or, where it is private, supplied by the
        operator's copy or a held one.'''
        if not source or urlsplit(source).query:
            return False
        scheme = urlsplit(source).scheme.lower()
        if scheme not in ("https", "http", "git+https"):
            # ssh and git:// want a key this server has not got, and no
            # resolver clones over plain http.
            return False
        return allowlist.allows(self.rules, download_url(source, ref)
                                if not scheme.startswith("git+") else source)

    def fetch(self, source: str, ref: Optional[str], timeout: float) -> str:
        '''Fetch and hold one source; return its root. Raises `Transient` or
        `Permanent`.'''
        found = self.held(source, ref)
        if found:
            return found
        if not self.allowlisted(source, ref):
            raise Permanent("not on this server's allowlist")

        where = self._key(source, ref)
        where.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".fetch-", dir=where))
        try:
            data = staging / "data"
            data.mkdir()
            pinned = self._resolve(source, ref, data, timeout)
            commit, moving = pinned if isinstance(pinned, tuple) else (None, False)
            # 🔴 The commit, recorded before `.git` went: what a job ran is
            # answerable after the fact. A moving ref -- a branch, or no ref --
            # is held for one job's staging and fetched again after it.
            (staging / _COMPLETE).write_text(json.dumps({
                "source": source, "ref": ref, "commit": commit, "moving": moving,
                "fetched_at": time.time()}))

            # A copy per fetch, never replaced under a job reading it; which
            # one is current moves atomically.
            copy = where / (commit if commit and not moving else staging.name[1:])
            try:
                os.rename(staging, copy)
            except OSError:
                _remove(staging)
            pointer = where / f".{_CURRENT}.{os.getpid()}"
            pointer.write_text(copy.name)
            os.replace(pointer, where / _CURRENT)
            return str(copy / "data")
        except BaseException:
            _remove(staging)
            raise

    ######################################################################

    def _resolve(self, source: str, ref: Optional[str], into: Path, timeout: float):
        '''SiliconCompiler's resolver for ``source``, run in a process of its
        own (`staging.fetch`), its result moved into ``into``. Returns
        ``(commit, moving)``: the commit a git source resolved to, and whether
        its ref moves. Raises `Transient` or `Permanent`.'''
        from siliconcompiler.package import RemoteResolver
        from siliconcompiler.remote.server.packages.envbuild import Proxy

        work = into.parent
        # A unix socket's path is bounded (108 bytes), and a data directory's
        # is not; so the socket gets a short directory of its own.
        sockets = Path(tempfile.mkdtemp(prefix="sc-fetch-"))
        proxy = Proxy(str(sockets / "proxy.sock"), [rule.text for rule in self.rules],
                      max_bytes=MAX_SOURCE_BYTES)
        proxy.start()
        try:
            answer = _run_fetch(source, ref, work, timeout, str(sockets / "proxy.sock"))
        except Transient:
            answer = None
            if not (proxy.refused or proxy.oversize):
                raise
        finally:
            proxy.close()
            shutil.rmtree(sockets, ignore_errors=True)

        # What the proxy refused explains the failure better than how the
        # resolver reported it.
        if proxy.refused:
            raise Permanent(f"it reaches {', '.join(proxy.refused)}, which this server "
                            "will not connect to: off its allowlist, or not a public "
                            "address")
        if proxy.oversize:
            raise Permanent(f"it is larger than {MAX_SOURCE_BYTES} bytes")
        if "error" in answer:
            failure = Permanent if answer["error"]["permanent"] else Transient
            raise failure(answer["error"]["message"])

        resolved = Path(answer["path"])
        commit, moving = _pin(resolved, ref)
        # The resolver leaves its cache read-only; this copy is moved out of it.
        _remove(resolved / ".git")
        RemoteResolver._make_writable(resolved)
        for child in list(resolved.iterdir()):
            shutil.move(str(child), str(into / child.name))
        for left in ("home", "cache"):
            _remove(work / left)
        for left in ("fetch.json", "result.json", "fetch.log"):
            (work / left).unlink(missing_ok=True)
        return commit, moving


def _run_fetch(source: str, ref: Optional[str], work: Path, timeout: float,
               proxy_socket: str) -> dict:
    '''Run `staging.fetch` for one source in ``work``, and return what it
    wrote. Raises `Transient` where it ran past ``timeout`` or wrote nothing.'''
    import subprocess

    from siliconcompiler.remote.server.staging import sandbox

    home = work / "home"
    home.mkdir()
    result = work / "result.json"
    spec = work / "fetch.json"
    spec.write_text(json.dumps({"source": source, "ref": ref, "cachedir": str(work / "cache"),
                                "proxy": proxy_socket, "result": str(result)}))
    # 🔴 Nothing of the server's: no token, no git configuration but the
    # repository's own, no prompt. PATH is where git is, and is no secret.
    env = {**sandbox._environment(home), "PATH": os.environ.get("PATH", os.defpath),
           "XDG_CONFIG_HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_TERMINAL_PROMPT": "0"}

    log = work / "fetch.log"
    with open(log, "wb") as out:
        process = subprocess.Popen(
            [*sandbox._python(), "-m", "siliconcompiler.remote.server.staging.fetch",
             str(spec)],
            env=env, cwd=str(home), stdin=subprocess.DEVNULL, stdout=out,
            stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        sandbox._kill(process)
        raise Transient(f"the fetch ran past its {int(timeout)}s") from None
    finally:
        if process.poll() is None:
            sandbox._kill(process)

    try:
        return json.loads(result.read_text())
    except (OSError, ValueError):
        tail = sandbox._tail(log)
        raise Transient(f"the fetch ended {sandbox._signal_name(process.returncode)}"
                        + (f": {tail}" if tail else "")) from None


def _pin(resolved: Path, ref: Optional[str]):
    '''``(commit, moving)`` for a git checkout; ``(None, False)`` for an
    archive, whose URL names its version.'''
    import re
    import subprocess

    if not (resolved / ".git").exists():
        return None, False

    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(resolved), *args], capture_output=True,
                                  text=True, timeout=30, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    commit = git("rev-parse", "HEAD")
    if not ref or ref == "HEAD":
        return commit, True
    if re.fullmatch(r"[0-9a-f]{40}", ref) or git("rev-parse", "--verify", "--quiet",
                                                 f"refs/tags/{ref}") is not None:
        return commit, False
    return commit, True


def _remove(path: Path) -> None:
    '''A tree the resolver may have made read-only.'''
    from siliconcompiler.package import RemoteResolver

    if not path.exists():
        return
    try:
        RemoteResolver._make_writable(path)
    except OSError:
        pass
    shutil.rmtree(path, ignore_errors=True)
