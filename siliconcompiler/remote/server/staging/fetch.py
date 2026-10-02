'''
One source fetched in a process of its own, held in from outside.

Started by :class:`~siliconcompiler.remote.server.staging.sources.SourceStore`::

    python -m siliconcompiler.remote.server.staging.fetch <spec.json>

it runs SiliconCompiler's own resolver for the source, unchanged, and writes
the spec's ``result`` -- the directory the source resolved to, or how the
fetch failed -- whatever happens.

🔴 **No resolver knows it runs here, so every one can.** What holds the fetch
in is the process around it, never a check inside a resolver:

- **nothing to send**: the server starts it with an environment of its own --
  an empty ``HOME``, no token, no git system configuration, no prompt -- so no
  resolver finds a token, a ``.netrc``, a credential helper or an SSH key;
- **one way out**: a network namespace of its own, where the kernel lets an
  unprivileged process have one, holding only a loopback, whose one route off
  the machine is the server's proxy on a unix socket. The proxy admits the
  allowlist's hosts, never a non-public address, and only so many bytes.
  Where there is no namespace, requests, git and git-lfs are pointed at the
  proxy by the environment instead.

⚠️ The proxy sees a host and a port for HTTPS, not a path: the allowlist's
paths bind the source a job names (`SourceStore.allowlisted`), and everything
the fetch reaches after it -- a redirect, a submodule, an LFS store -- is held
to the allowlist's hosts.
'''

import json
import os
import re
import socket
import sys

from pathlib import Path
from typing import Any, Dict, Optional

__all__ = ["classify", "main"]


# What a source's answer means for the job: one of these goes back to the
# client, which has the credentials this server does not -- GitHub answers 404
# for a private repository it will not show. A 429 or a 5xx is retried.
_PERMANENT = (401, 403, 404, 410)

# How `HTTPResolver` reports a download the source refused.
_STATUS = re.compile(r"Status code: (\d+)")

# What git says for a source that refused, or has no such ref.
_GIT_REFUSALS = ("not found", "authentication", "could not read username",
                 "couldn't find remote ref", "did not match any", "403", "401")


def isolate() -> bool:
    '''Give this process a network namespace of its own, holding a loopback
    that is up. Returns whether it has one.'''
    unshare = getattr(os, "unshare", None)
    if unshare is None or not sys.platform.startswith("linux"):
        return False
    uid, gid = os.getuid(), os.getgid()
    try:
        # A user namespace is what lets an unprivileged process have the
        # network one.
        unshare(os.CLONE_NEWUSER | os.CLONE_NEWNET)
    except OSError:
        return False
    # The same ids inside as out, so what the resolver writes is the server's.
    Path("/proc/self/setgroups").write_text("deny")
    Path("/proc/self/uid_map").write_text(f"{uid} {uid} 1")
    Path("/proc/self/gid_map").write_text(f"{gid} {gid} 1")
    _loopback_up()
    return True


def _loopback_up() -> None:
    '''A new network namespace's loopback starts down.'''
    import fcntl
    import struct

    SIOCGIFFLAGS, SIOCSIFFLAGS, IFF_UP = 0x8913, 0x8914, 0x1
    ifreq = "16sH22x"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        flags = struct.unpack(ifreq, fcntl.ioctl(s, SIOCGIFFLAGS,
                                                 struct.pack(ifreq, b"lo", 0)))[1]
        fcntl.ioctl(s, SIOCSIFFLAGS, struct.pack(ifreq, b"lo", flags | IFF_UP))


def _through(proxy_socket: str) -> None:
    '''Point everything this process starts at the proxy on ``proxy_socket``.'''
    from siliconcompiler.remote.server.packages.pipbuild import _forward

    proxy = f"http://127.0.0.1:{_forward(proxy_socket)}"
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        os.environ[name] = proxy
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = ""


def resolve(source: str, ref: Optional[str], cachedir: str) -> str:
    '''SiliconCompiler's resolver for ``source``, as any project runs it.
    Returns the directory it resolved to.'''
    from siliconcompiler import Project
    from siliconcompiler.package import Resolver

    project = Project("sc-server-source")
    project.option.set_cachedir(cachedir)
    resolver = Resolver.find_resolver(source)("source", project, source, ref or "HEAD")
    return str(resolver.resolve())


def classify(error: BaseException) -> Dict[str, Any]:
    '''A resolver's failure, as what the job does about it:
    ``{"permanent", "message"}``. A permanent one goes back to the client; a
    transient one is retried until the job's deadline.'''
    import requests

    from siliconcompiler.package import Resolver

    found = _STATUS.search(str(error)) if isinstance(error, OSError) else None
    if found:
        status = int(found.group(1))
        return {"permanent": status in _PERMANENT or not (status == 429 or status >= 500),
                "message": f"the source answered {status}"}
    # SiliconCompiler's own rule, which reads nothing of the resolver's.
    if Resolver.is_permanent_failure(None, error):
        return {"permanent": True, "message": str(error)}
    if isinstance(error, requests.RequestException):
        return {"permanent": False,
                "message": f"could not reach the source: {type(error).__name__}"}
    if any(word in str(error).lower() for word in _GIT_REFUSALS):
        return {"permanent": True, "message": "the git source refused, or has no such ref"}
    if isinstance(error, TypeError):
        return {"permanent": True,
                "message": f"the source is not an archive this server can unpack: {error}"}
    return {"permanent": False, "message": f"the source failed: {type(error).__name__}"}


def main(argv=None) -> int:
    '''Isolate, fetch, write the result. The spec is argv's one argument: a
    JSON file naming ``source``, ``ref``, ``cachedir``, ``proxy`` (the
    proxy's unix socket) and ``result``.'''
    argv = sys.argv[1:] if argv is None else argv
    spec = json.loads(Path(argv[0]).read_text())

    result: Dict[str, Any] = {}
    try:
        result["contained"] = isolate()
        _through(spec["proxy"])
    except OSError as e:
        # This server's failure, not the source's.
        result["error"] = {"permanent": False,
                           "message": f"this server could not isolate the fetch: {e}"}
    else:
        try:
            result["path"] = resolve(spec["source"], spec.get("ref"), spec["cachedir"])
        except Exception as e:                                   # noqa: BLE001
            result["error"] = classify(e)
    Path(spec["result"]).write_text(json.dumps(result))
    return 0


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
