'''
Building a job's Python packages into an image (surface *How it is built,
while the job is staging*; implementation-notes §L).

The container mode of a job's Python: the image a node resolved to with the
job's `python_packages` and uploaded wheels installed in one layer of its own,
pushed to the registry beside it and staged as a bundle, so every node of the
job that runs the user's Python on that image runs from one image with no
network at all. Run as a job of its own on a compute node -- the builder queue
-- by the API while the job is ``staging``::

    python -m siliconcompiler.remote.server.envbuild <workspace>/spec.json

and it writes ``<workspace>/result.json`` whatever happens, which is all the
API reads. The workspace holds the requirements and constraints files the API
wrote from what parsed, and the job's wheels under ``wheels/``.

🔴 **Isolated, and each part of that is load-bearing** (contract item 3):

- **pip runs inside the base image**, under the Python the node will run, so
  markers and wheels are chosen for it rather than for this host;
- **in a container of its own** -- read-only root, a private /tmp, and none of
  the base's bind mounts, so no PDK, no build tree, no cluster socket;
- **with a network namespace holding only a loopback**. Its one way out is a
  unix socket bound in from here, to a proxy that admits the hosts of
  `index_allowlist` and nothing else, and never a non-public address;
- **from the deployment's `package_indexes`** -- a job names none -- and a
  source distribution may be built here, and only here: its code runs with no
  PDK data, no credential but an index's own, and no network but the
  configured indexes.

⚠️ The proxy sees a host and a port for HTTPS, not a path: an https entry of
`index_allowlist` admits its whole host here.
'''

import copy
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

__all__ = ["SPEC", "RESULT", "REQUIREMENTS", "CONSTRAINTS", "WHEELS", "LOG", "build",
           "build_config", "Proxy", "wait_for"]


SPEC = "spec.json"
RESULT = "result.json"
REQUIREMENTS = "requirements.txt"
CONSTRAINTS = "constraints.txt"
WHEELS = "wheels"
LOG = "build.log"

# Inside the build container.
_REQ = "/tmp/sc-req"
_OUT = "/tmp/sc-out"
_PROXY = "/tmp/sc-proxy"

_HEAD_LIMIT = 64 * 1024
_CONNECT_TIMEOUT = 30


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    spec_path = Path(argv[0])
    workspace = spec_path.parent
    try:
        spec = json.loads(spec_path.read_text())
        result = build(spec, workspace)
    except Exception as e:                                      # noqa: BLE001
        result = {"ok": False, "reason": "error", "detail": f"{type(e).__name__}: {e}"}
    _write_result(workspace, result)
    print(json.dumps(result, indent=1))
    return 0


def build(spec: Dict[str, Any], workspace: Path, run=None) -> Dict[str, Any]:
    '''One environment into a derived image. Returns the result record.

    ``run`` starts the build container and waits for it; the default is
    `_run_container`. Tests hand in their own.
    '''
    from siliconcompiler.remote.server import images, oci, pipbuild

    root = Path(spec["bundles_root"])
    base = images.stage_bundle(root, spec["base_ref"], spec["base_digest"],
                               mounts=spec.get("mounts") or [])

    req = workspace / "req"
    out = workspace / "out"
    for directory in (req, out):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)
    shutil.copy(workspace / REQUIREMENTS, req / REQUIREMENTS)
    shutil.copy(workspace / CONSTRAINTS, req / CONSTRAINTS)
    wheels = sorted((workspace / WHEELS).glob("*.whl")) \
        if (workspace / WHEELS).is_dir() else []
    if wheels:
        (req / WHEELS).mkdir()
        for wheel in wheels:
            shutil.copy(wheel, req / WHEELS / wheel.name)
    shutil.copy(pipbuild.__file__, req / "pipbuild.py")

    # A unix socket's path is bounded (108 bytes), and a workspace under a data
    # directory is not; so the socket gets a short directory of its own.
    sockets = Path(tempfile.mkdtemp(prefix="sc-envb-"))
    try:
        with open(base / "config.json") as f:
            base_spec = json.load(f)
        bundle = workspace / "bundle"
        shutil.rmtree(bundle, ignore_errors=True)
        bundle.mkdir()
        command = ["python3", f"{_REQ}/pipbuild.py",
                   "--requirements", f"{_REQ}/{REQUIREMENTS}",
                   "--constraints", f"{_REQ}/{CONSTRAINTS}",
                   "--site", f"{_OUT}/site", "--result", f"{_OUT}/pip.json",
                   "--proxy-socket", f"{_PROXY}/proxy.sock"]
        for wheel in wheels:
            command += ["--wheel", f"{_REQ}/{WHEELS}/{wheel.name}"]
        # The deployment's indexes, and a source distribution may be built:
        # this container is the one place isolated enough to run its code.
        for index in spec.get("indexes") or []:
            command += ["--index-url", index]
        command.append("--allow-source")
        config = build_config(base_spec, base / "rootfs", req, out, sockets, command)
        with open(bundle / "config.json", "w") as f:
            json.dump(config, f, indent=1)

        proxy = Proxy(str(sockets / "proxy.sock"), spec.get("index_allowlist") or [],
                      private_exact_hosts=True)
        proxy.start()
        try:
            output = (run or _run_container)(bundle, command, _image_path(base_spec),
                                             int(spec.get("timeout") or 1800))
        finally:
            proxy.close()
    finally:
        shutil.rmtree(sockets, ignore_errors=True)
        shutil.rmtree(workspace / "bundle", ignore_errors=True)

    try:
        pip = json.loads((out / "pip.json").read_text())
    except (OSError, ValueError):
        return {"ok": False, "reason": "error",
                "detail": "the build container did not run to the end:\n" + _tail(output)}

    facts = {"python": pip.get("python"), "version": pip.get("version"),
             "platform": pip.get("platform"), "ignored": pip.get("ignored") or {}}
    if pip.get("absent"):
        # A package no configured index has: the job is sent back for it.
        return {"ok": False, "reason": "absent", **facts, "absent": pip["absent"],
                "tail": pip.get("tail", "")}
    if pip.get("returncode") != 0:
        # 🔴 A refused host is policy, and says so; a network that did not
        # answer says nothing about the pins, so it is the server's failure
        # rather than the job's.
        if pip.get("network") and not proxy.refused:
            return {"ok": False, "reason": "error", **facts,
                    "detail": "the build could not reach an index:\n" + pip.get("tail", "")}
        return {"ok": False, "reason": "uninstallable", **facts,
                "unresolved": pip.get("unresolved") or [], "refused": proxy.refused,
                "tail": pip.get("tail", "")}

    site = out / "site"
    site.mkdir(exist_ok=True)
    layer = oci.layer_from(site, images.LAYER_PATH)
    ref, digest = oci.derive(spec["base_ref"], layer,
                             comment=spec.get("comment") or "sc-server environment")
    images.stage_derived_bundle(root, spec["base_digest"], digest, site)
    shutil.rmtree(out, ignore_errors=True)
    return {"ok": True, "ref": ref, "digest": digest,
            "installed": pip.get("installed") or [],
            "substituted": pip.get("substituted") or {}, **facts}


def build_config(base: Dict[str, Any], rootfs: Path, req: Path, out: Path,
                 sockets: Path, command: List[str]) -> Dict[str, Any]:
    '''The build container's OCI configuration, from its base image's.

    The base's process, namespaces and devices, with what makes it a builder:
    its root read-only, none of its bind mounts, a private /tmp, the three
    directories the build uses bound under it, and a network namespace of its
    own. Absolute ``root.path``, so it needs no copy of the base's filesystem.
    '''
    spec = copy.deepcopy(base)
    spec["root"] = {"path": str(Path(rootfs).resolve()), "readonly": True}
    spec["hostname"] = "sc-envbuild"

    from siliconcompiler.remote.server.images import drop_capabilities

    drop_capabilities(spec)
    process = spec.setdefault("process", {})
    process["terminal"] = False
    process["cwd"] = "/tmp"
    process["args"] = list(command)
    process["env"] = [f"PATH={_image_path(base)}", "HOME=/tmp", "LANG=C.UTF-8",
                      "PYTHONNOUSERSITE=1"]

    kept = []
    for mount in spec.get("mounts") or []:
        options = mount.get("options") or []
        if mount.get("type") == "bind" or "bind" in options or "rbind" in options:
            continue
        if mount.get("type") == "cgroup" or mount.get("destination") == "/sys/fs/cgroup":
            continue
        kept.append(mount)
    kept.append({"destination": "/tmp", "type": "tmpfs", "source": "tmpfs",
                 "options": ["nosuid", "nodev", "mode=1777", "size=67108864"]})
    for where, source, mode in ((_REQ, req, "ro"), (_OUT, out, "rw"), (_PROXY, sockets, "rw")):
        kept.append({"destination": where, "type": "bind", "source": str(source),
                     "options": ["rbind", mode, "nosuid", "nodev"]})
    spec["mounts"] = kept

    linux = spec.setdefault("linux", {})
    namespaces = [entry for entry in linux.get("namespaces") or []
                  if entry.get("type") != "network"]
    namespaces.append({"type": "network"})
    linux["namespaces"] = namespaces
    return spec


def _image_path(base: Dict[str, Any]) -> str:
    for entry in (base.get("process") or {}).get("env") or []:
        if entry.startswith("PATH="):
            return entry[5:]
    return "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _run_container(bundle: Path, command: List[str], path: str, timeout: int) -> str:
    '''Start the build container and wait for it. Returns what it printed.

    ``srun --container`` inside this build's own allocation, as a node runs --
    the cluster's runtime and its configuration. Off a cluster, crun directly.
    '''
    env = {key: value for key, value in os.environ.items() if key.startswith("SLURM_")}
    env.update({"PATH": path, "HOME": "/tmp", "LANG": "C.UTF-8"})

    if os.environ.get("SLURM_JOB_ID") and shutil.which("srun"):
        launch = ["srun", "--ntasks=1", f"--container={bundle}", "--chdir=/tmp", *command]
        env["PATH"] = os.pathsep.join([path, os.environ.get("PATH", "")])
    elif shutil.which("crun"):
        state = tempfile.mkdtemp(prefix="sc-crun-")
        launch = ["crun", f"--root={state}", "run", "--no-new-keyring",
                  "--bundle", str(bundle), f"sc-envbuild-{os.getpid()}"]
        env["PATH"] = os.environ.get("PATH", path)
    else:
        raise RuntimeError("no container runtime here to build in: neither a Slurm "
                           "allocation with srun nor crun")

    try:
        done = subprocess.run(launch, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
        output = done.stdout
    except subprocess.TimeoutExpired as e:
        output = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) \
            else (e.stdout or "")
        output += f"\nthe build took longer than {timeout}s and was stopped"
    sys.stdout.write(output)
    return output


def _tail(text: str, lines: int = 20) -> str:
    return "\n".join((text or "").strip().splitlines()[-lines:])


def _write_result(workspace: Path, result: Dict[str, Any]) -> None:
    '''Written whole and renamed into place: the API polls for it, and must
    never read half of one.'''
    staging = workspace / f".{RESULT}.{os.getpid()}"
    staging.write_text(json.dumps(result))
    os.replace(staging, workspace / RESULT)


######################################################################
# The proxy: the build's only way out
######################################################################

class Proxy:
    '''An HTTP proxy that admits an allowlist, and nothing else.

    On a unix socket (``address`` a path) for the build container, or on
    loopback (``address`` a ``(host, port)``) for the git a source fetch runs.
    ``CONNECT host:port`` for HTTPS, admitted when an https entry names that
    host and port; a plain ``GET``/``HEAD`` for an ``http://`` URL, admitted
    when the whole URL is under an entry.

    🔴 **Never to a private, loopback or link-local address**, whatever
    resolves to one -- `allowlist.public_host`'s rule, for every fetch this
    server makes -- with one exception, for the builder only
    (``private_exact_hosts``, surface D172): an index entry naming one exact
    host is the operator's choice of a machine, a mirror on their own network,
    and may resolve to a private address. A wildcard entry never may, and no
    source-allowlist entry does.

    ``refused`` lists every host it said no to, for the result to name.
    '''

    def __init__(self, address, entries, private_exact_hosts: bool = False):
        from siliconcompiler.remote.server import allowlist

        self._rules = [allowlist.parse(entry) for entry in entries]
        self._hosts = [rule._replace(segments=()) for rule in self._rules
                       if rule.scheme == "https"]
        self._private_exact = private_exact_hosts
        self.refused: List[str] = []
        if isinstance(address, tuple):
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.bind(address)
            self.url = "http://%s:%d" % self._socket.getsockname()[:2]
        else:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.bind(address)
            self.url = None
        self._socket.listen(64)
        self._closed = False

    def start(self) -> None:
        threading.Thread(target=self._serve, daemon=True, name="envbuild-proxy").start()

    def close(self) -> None:
        self._closed = True
        try:
            self._socket.close()
        except OSError:                                         # pragma: no cover
            pass

    def admits_connect(self, host: str, port: int) -> bool:
        return self._matching(self._hosts, f"https://{host}:{port}/") is not None

    def admits_get(self, url: str) -> bool:
        return urlsplit(url).scheme == "http" and \
            self._matching(self._rules, url) is not None

    @staticmethod
    def _matching(rules, url: str):
        from siliconcompiler.remote.server import allowlist

        for rule in rules:
            if allowlist.allows([rule], url):
                return rule
        return None

    def _public_only(self, rules, url: str) -> bool:
        '''Whether the address rule binds this connection: always, but for
        an exact-host entry where the exception is on.'''
        rule = self._matching(rules, url)
        return not (self._private_exact and rule is not None
                    and not rule.host.startswith("*."))

    def _serve(self) -> None:
        while not self._closed:
            try:
                client, _ = self._socket.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    def _handle(self, client) -> None:
        upstream = None
        try:
            head, rest = _read_head(client)
            if head is None:
                return
            line, _, headers = head.partition(b"\r\n")
            try:
                method, target, _ = line.decode("latin-1").split(" ", 2)
            except ValueError:
                return _answer(client, 400, "a request line")

            if method == "CONNECT":
                host, _, port = target.rpartition(":")
                host = host.strip("[]").lower()
                if not port.isdigit() or not self.admits_connect(host, int(port)):
                    return self._refuse(client, host)
                upstream = _open_public(host, int(port), public_only=self._public_only(
                    self._hosts, f"https://{host}:{port}/"))
                if upstream is None:
                    return self._refuse(client, host, "resolves to a non-public address")
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
            elif method in ("GET", "HEAD") and target.startswith("http://"):
                parts = urlsplit(target)
                if not self.admits_get(target):
                    return self._refuse(client, (parts.hostname or "").lower())
                upstream = _open_public(parts.hostname, parts.port or 80,
                                        public_only=self._public_only(self._rules, target))
                if upstream is None:
                    return self._refuse(client, parts.hostname,
                                        "resolves to a non-public address")
                path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
                kept = [header for header in headers.split(b"\r\n") if header and not
                        header.lower().startswith((b"proxy-", b"connection:"))]
                upstream.sendall(f"{method} {path} HTTP/1.1\r\n".encode("latin-1")
                                 + b"\r\n".join(kept + [b"Connection: close"])
                                 + b"\r\n\r\n" + rest)
            else:
                return _answer(client, 405, "CONNECT, or GET and HEAD for http")

            _splice(client, upstream)
        except OSError:
            pass
        finally:
            for end in (client, upstream):
                if end is not None:
                    try:
                        end.close()
                    except OSError:                             # pragma: no cover
                        pass

    def _refuse(self, client, host: str, why: str = "is not on the allowlist"):
        if host and host not in self.refused:
            self.refused.append(host)
        print(f"proxy: refused {host}: it {why}", flush=True)
        _answer(client, 403, f"{host} {why}")


def _read_head(client) -> Tuple[Optional[bytes], bytes]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = client.recv(8192)
        if not chunk:
            return None, b""
        data += chunk
        if len(data) > _HEAD_LIMIT:
            return None, b""
    head, _, rest = data.partition(b"\r\n\r\n")
    return head, rest


def _answer(client, status: int, why: str) -> None:
    reason = {400: "Bad Request", 403: "Forbidden", 405: "Method Not Allowed"}[status]
    body = f"{why}\n".encode()
    try:
        client.sendall(f"HTTP/1.1 {status} {reason}\r\nContent-Length: {len(body)}\r\n"
                       f"Connection: close\r\n\r\n".encode() + body)
    except OSError:                                             # pragma: no cover
        pass


def _open_public(host: str, port: int, public_only: bool = True):
    '''A connection to ``host`` -- where every address it resolves to is
    public, unless ``public_only`` is off -- and to one of the addresses
    checked, never a second lookup.'''
    import ipaddress

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return None
    if public_only:
        for info in infos:
            try:
                address = ipaddress.ip_address(info[4][0])
            except ValueError:
                return None
            if not address.is_global or address.is_multicast:
                return None
    for family, kind, proto, _, where in infos:
        connection = socket.socket(family, kind, proto)
        connection.settimeout(_CONNECT_TIMEOUT)
        try:
            connection.connect(where)
            connection.settimeout(None)
            return connection
        except OSError:
            connection.close()
    return None


def _splice(one, other) -> None:
    def pipe(source, sink):
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                sink.sendall(data)
        except OSError:
            pass
        finally:
            try:
                sink.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    back = threading.Thread(target=pipe, args=(other, one), daemon=True)
    back.start()
    pipe(one, other)
    back.join()


def wait_for(workspace: Path, timeout: float, alive=None, pause: float = 2.0,
             ask_every: float = 30.0, grace: float = 15.0):
    '''The result of a build, once it is written; None past ``timeout``, or
    ``grace`` seconds after ``alive()`` first says the build job is gone
    without one.

    The file is looked for every ``pause``; the scheduler is asked at most
    every ``ask_every``, since each ask is a call into it. The grace is for a
    shared filesystem, where a file written on the compute node can appear here
    after the job that wrote it has ended.
    '''
    deadline = time.monotonic() + timeout
    path = Path(workspace) / RESULT
    asked = gone = None
    while True:
        if path.is_file():
            try:
                return json.loads(path.read_text())
            except ValueError:                                  # pragma: no cover
                pass
        now = time.monotonic()
        if now >= deadline:
            return None
        if gone is not None:
            if now - gone >= grace:
                return None
        elif alive is not None and (asked is None or now - asked >= ask_every):
            asked = now
            if not alive():
                gone = now
        time.sleep(pause)


if __name__ == "__main__":
    sys.exit(main())
