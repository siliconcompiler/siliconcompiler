'''
The server's own copies of remote sources: held, and fetched only from the
allowlist.

A job's remote dataroot -- lambdapdk's PDKs are the common case -- is supplied
by (source, ref), never by a path the job names. This module holds those
copies under ``<datadir>/sources/`` and fetches the ones it does not hold.

🔴 **The run never fetches.** The server's normalised manifest points a supplied
dataroot at the held copy, so SiliconCompiler's own resolver -- which follows
any redirect to any host -- is never what reaches the network on a job's
behalf. Everything that does goes through here:

- the URL is on the allowlist, and so is **every redirect hop**;
- the host resolves only to public addresses, at every hop;
- nothing is sent with it: no credentials, no prompt, no credential helper.

⚠️ **Failures are two kinds, and the difference decides what the job does.** A
transient one -- ``429``, a ``5xx``, a timeout -- is retried until the job's
deadline, or a GitHub blip becomes a multi-gigabyte upload. A permanent one --
``401``, ``403``, ``404`` -- sends the job back to ask the client, which has
the credentials the server does not: GitHub answers ``404`` for a private
repository it will not show.
'''

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile

from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urljoin, urlsplit

from siliconcompiler.remote.server import allowlist

__all__ = ["SourceStore", "Transient", "Permanent", "download_url"]


logger = logging.getLogger("sc-server")

# How many redirects one fetch may follow. GitHub's archive takes one.
MAX_HOPS = 5

# The most one source may weigh, downloaded. A PDK is gigabytes; this is a
# ceiling on a mistake, not a budget.
MAX_SOURCE_BYTES = 16 * 1024 ** 3

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
        '''The held copy's root, or None where this server has not got it.'''
        if not source:
            return None
        where = self._key(source, ref)
        if (where / ".complete").is_file():
            return str(where / "data")
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

    def fetch(self, source: str, ref: Optional[str], timeout: float,
              session=None) -> str:
        '''Fetch and hold one source; return its root. Raises `Transient` or
        `Permanent`.'''
        found = self.held(source, ref)
        if found:
            return found
        if not self.allowlisted(source, ref):
            raise Permanent("not on this server's allowlist")

        where = self._key(source, ref)
        self.root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".fetch-", dir=self.root))
        try:
            data = staging / "data"
            data.mkdir()
            if urlsplit(source).scheme.lower().startswith("git+"):
                self._git(source, ref, data, timeout)
            else:
                self._archive(download_url(source, ref), data, timeout, session)
            (staging / ".complete").write_text(f"{source}\n{ref or ''}\n")

            # Atomic, and first one wins: two jobs fetching the same source at
            # once both end up with one copy.
            try:
                os.rename(staging, where)
            except OSError:
                shutil.rmtree(staging, ignore_errors=True)
            return str(where / "data")
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    ######################################################################

    def _archive(self, url: str, into: Path, timeout: float, session) -> None:
        import requests

        from siliconcompiler.package.https import _extract_archive

        session = session or requests.Session()
        # SiliconCompiler flattens GitHub's archives only, by the URL it asked.
        github = "github" in url
        for _ in range(MAX_HOPS + 1):
            self._check(url)
            try:
                response = session.get(url, stream=True, timeout=timeout,
                                       allow_redirects=False)
            except requests.RequestException as e:
                raise Transient(f"could not reach the source: {type(e).__name__}") from None

            if response.status_code in (301, 302, 303, 307, 308):
                target = response.headers.get("Location")
                response.close()
                if not target:
                    raise Permanent("redirected without saying where")
                url = urljoin(url, target)
                continue

            if response.status_code in _PERMANENT:
                raise Permanent(f"the source answered {response.status_code}")
            if response.status_code == 429 or response.status_code >= 500:
                raise Transient(f"the source answered {response.status_code}")
            if response.status_code != 200:
                raise Permanent(f"the source answered {response.status_code}")

            with tempfile.TemporaryFile(dir=self.root) as body:
                size = 0
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_SOURCE_BYTES:
                        raise Permanent("the source is larger than this server fetches")
                    body.write(chunk)
                body.seek(0)
                try:
                    _extract_archive(body, str(into), url)
                except Exception as e:                           # noqa: BLE001
                    raise Permanent(f"the source is not an archive this server "
                                    f"can unpack: {type(e).__name__}") from None
            if github:
                _flatten(into)
            return

        raise Permanent("too many redirects")

    def _git(self, source: str, ref: Optional[str], into: Path, timeout: float) -> None:
        url = source[4:]            # git+https://... -> https://...
        self._check(url)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.root),
               "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false",
               "GIT_CONFIG_NOSYSTEM": "1"}
        base = ["git", "-c", "http.followRedirects=false", "-c", "credential.helper=",
                "-c", "protocol.allow=never", "-c", "protocol.https.allow=always"]
        steps = [base + ["init", "-q", str(into)],
                 base + ["-C", str(into), "fetch", "-q", "--depth", "1", url, ref or "HEAD"],
                 base + ["-C", str(into), "checkout", "-q", "FETCH_HEAD"]]
        for step in steps:
            try:
                done = subprocess.run(step, env=env, capture_output=True, text=True,
                                      timeout=timeout, check=False)
            except subprocess.TimeoutExpired:
                raise Transient("the git source timed out") from None
            if done.returncode:
                said = (done.stderr or "").lower()
                if any(word in said for word in ("not found", "authentication",
                                                 "could not read username",
                                                 "couldn't find remote ref", "403", "401")):
                    raise Permanent("the git source refused or has no such ref")
                raise Transient("the git source failed")
        shutil.rmtree(into / ".git", ignore_errors=True)

    def _check(self, url: str) -> None:
        '''Every hop: on the allowlist, and to a public address.'''
        if not allowlist.allows(self.rules, url):
            raise Permanent("a redirect left this server's allowlist")
        parts = urlsplit(url)
        if not allowlist.public_host(parts.hostname or "", parts.port):
            raise Permanent("the source's host is not a public address")


def _flatten(into: Path) -> None:
    '''GitHub's archives carry one top-level directory; SiliconCompiler's
    resolver moves its contents up, and so does this, so a held copy is laid
    out as the run expects. Only for GitHub, as the resolver does.'''
    entries = list(into.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return
    top = entries[0]
    for child in list(top.iterdir()):
        shutil.move(str(child), str(into / child.name))
    top.rmdir()
