'''
The server's own copies of remote sources: held, and fetched only from the
allowlist.

A job's remote dataroot -- lambdapdk's PDKs are the common case -- is supplied
by (source, ref), never by a path the job names. This module holds those
copies under ``<datadir>/sources/`` and fetches the ones it does not hold.

🔴 **The run never fetches.** The server's normalised manifest points a supplied
dataroot at the held copy, so nothing in the run reaches the network on a job's
behalf. What does is here, and it is SiliconCompiler's own resolver -- so the
server's copy is the user's, submodules and LFS objects included (surface
D164) -- under a fetch policy:

- no credentials at all: no token, no credential helper, no SSH agent or key,
  an empty ``HOME``, https only;
- every URL it contacts on the allowlist and to a public address: each
  redirect hop, each submodule's URL, the LFS endpoint -- and everything git
  and git-lfs connect to through a proxy that applies the same rules, for what
  cannot be seen from here, such as an LFS object's storage host.

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

from siliconcompiler.remote.server import allowlist

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

_PERMANENT = (401, 403, 404, 410)


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

    def commit(self, source: Optional[str], ref: Optional[str]) -> Optional[str]:
        '''The commit the held copy resolved to, where it came from git.'''
        found = self.held(source, ref)
        if not found:
            return None
        try:
            return json.loads((Path(found).parent / _COMPLETE).read_text()).get("commit")
        except (OSError, ValueError):
            return None

    def allowlisted(self, source: Optional[str], ref: Optional[str]) -> bool:
        '''Whether this server would fetch the source itself.'''
        if not source:
            return False
        scheme = urlsplit(source).scheme.lower()
        if scheme not in ("https", "http", "git+https", "git+http"):
            # ssh and git:// want a key this server has not got.
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
        '''SiliconCompiler's resolver for ``source``, run under the fetch
        policy, its result moved into ``into``. Returns ``(commit, moving)``:
        the commit a git source resolved to, and whether its ref moves.'''
        from siliconcompiler import Project
        from siliconcompiler.package import FetchPolicy, RemoteResolver, Resolver, fetch_policy
        from siliconcompiler.remote.server.envbuild import Proxy

        work = into.parent
        home = work / "home"
        home.mkdir()
        project = Project("sc-server-source")
        project.option.set_cachedir(str(work / "cache"))
        resolver = Resolver.find_resolver(source)("source", project, source, ref or "HEAD")

        proxy = Proxy(("127.0.0.1", 0), [rule.text for rule in self.rules])
        proxy.start()
        try:
            policy = FetchPolicy(check_url=self._check, home=str(home), proxy=proxy.url,
                                 timeout=timeout, max_bytes=MAX_SOURCE_BYTES)
            with fetch_policy(policy):
                resolved = Path(resolver.resolve())
        except BaseException as e:
            raise _classified(e, proxy.refused) from None
        finally:
            proxy.close()

        commit, moving = _pin(resolved, ref)
        # The resolver leaves its cache read-only; this copy is moved out of it.
        _remove(resolved / ".git")
        RemoteResolver._make_writable(resolved)
        for child in list(resolved.iterdir()):
            shutil.move(str(child), str(into / child.name))
        return commit, moving

    def _check(self, url: str) -> None:
        '''Every URL the resolver contacts: on the allowlist, and to a public
        address.'''
        from siliconcompiler.package import FetchRefused

        if not allowlist.allows(self.rules, url):
            raise FetchRefused(f"{url} is off this server's allowlist")
        parts = urlsplit(url)
        if not allowlist.public_host(parts.hostname or "", parts.port):
            raise FetchRefused(f"{parts.hostname} is not a public address")


def _classified(error: BaseException, refused) -> BaseException:
    '''A resolver's failure, as what the job does about it: `Permanent` goes
    back to the client, `Transient` is retried until the job's deadline.'''
    import requests

    from siliconcompiler.package import FetchRefused
    from siliconcompiler.package.cache import PermanentResolutionError

    if isinstance(error, (Permanent, Transient, KeyboardInterrupt, SystemExit)):
        return error
    if refused:
        return Permanent(f"it reaches {', '.join(refused)}, which this server's "
                         "allowlist does not name")
    if isinstance(error, (FetchRefused, PermanentResolutionError)):
        return Permanent(str(error))
    status = getattr(error, "status", None)
    if status is not None:
        if status in _PERMANENT:
            return Permanent(f"the source answered {status}")
        if status == 429 or status >= 500:
            return Transient(f"the source answered {status}")
        return Permanent(f"the source answered {status}")
    if isinstance(error, requests.RequestException):
        return Transient(f"could not reach the source: {type(error).__name__}")
    said = str(error).lower()
    if any(word in said for word in ("not found", "authentication", "could not read username",
                                     "couldn't find remote ref", "did not match any",
                                     "403", "401", "not a plain https", "only https")):
        return Permanent("the git source refused, or has no such ref")
    if isinstance(error, TypeError):
        return Permanent(f"the source is not an archive this server can unpack: {error}")
    return Transient(f"the source failed: {type(error).__name__}")


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
