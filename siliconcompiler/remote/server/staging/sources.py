'''
The server's own copies of remote sources, held under ``<datadir>/sources/`` by
(source, ref) and fetched only from the allowlist.

🔴 The run never fetches: it points a supplied dataroot at the held copy
(`runspec.point_dataroots`). The fetch is SiliconCompiler's own resolver,
submodules and LFS included (surface D164), isolated in `staging.fetch`.

⚠️ A transient failure (``429``, ``5xx``, timeout) is retried until the job's
deadline, or a GitHub blip becomes a huge upload; a permanent one (``401``,
``403``, ``404``) asks the client, which has the credentials.
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

# A ceiling on a mistake, not a budget: a PDK is gigabytes.
MAX_SOURCE_BYTES = 16 * 1024 ** 3

# A moving ref's copy stands for one job's staging, never the next job's.
MOVING_HOLD_SECONDS = 3600

_COMPLETE = ".complete"
_CURRENT = "current"


class Transient(Exception):
    '''A fetch that may work if tried again.'''


class Permanent(Exception):
    '''A fetch that will not work from here: the client must send it.'''


def download_url(source: str, ref: Optional[str]) -> str:
    '''The URL SiliconCompiler's https resolver would fetch for this source.'''
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
        '''The held copy's root, or None where there is none still current.'''
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

        🔴 Never one whose URL has a query (surface D308): its values are masked.'''
        if not source or urlsplit(source).query:
            return False
        scheme = urlsplit(source).scheme.lower()
        if scheme not in ("https", "http", "git+https"):
            # ssh and git:// want a key this server has not got.
            return False
        return allowlist.allows(self.rules, download_url(source, ref)
                                if not scheme.startswith("git+") else source)

    def fetch(self, source: str, ref: Optional[str], timeout: float) -> str:
        '''Fetch and hold one source; returns its root.'''
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
            # 🔴 The commit, recorded before `.git` goes, so what a job ran stays answerable.
            (staging / _COMPLETE).write_text(json.dumps({
                "source": source, "ref": ref, "commit": commit, "moving": moving,
                "fetched_at": time.time()}))

            # A copy per fetch, never replaced under a reader; `current` moves atomically.
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

    def _resolve(self, source: str, ref: Optional[str], into: Path, timeout: float):
        '''Resolve ``source`` in `staging.fetch` into ``into``; returns ``(commit, moving)``.'''
        from siliconcompiler.package import RemoteResolver
        from siliconcompiler.remote.server.packages.envbuild import Proxy

        work = into.parent
        # A unix socket's path is bounded (108 bytes), so a short directory.
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

        # The proxy's refusal explains the failure better than the resolver.
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
    '''Run `staging.fetch` for one source in ``work``; returns what it wrote.'''
    import subprocess

    from siliconcompiler.remote.server.staging import sandbox

    home = work / "home"
    home.mkdir()
    result = work / "result.json"
    spec = work / "fetch.json"
    spec.write_text(json.dumps({"source": source, "ref": ref, "cachedir": str(work / "cache"),
                                "proxy": proxy_socket, "result": str(result)}))
    # 🔴 Nothing of the server's: no token, no git config but the repo's, no prompt.
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
    '''``(commit, moving)`` for a git checkout; ``(None, False)`` for an archive.'''
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
    '''Remove a tree the resolver may have made read-only.'''
    from siliconcompiler.package import RemoteResolver

    if not path.exists():
        return
    try:
        RemoteResolver._make_writable(path)
    except OSError:
        pass
    shutil.rmtree(path, ignore_errors=True)
