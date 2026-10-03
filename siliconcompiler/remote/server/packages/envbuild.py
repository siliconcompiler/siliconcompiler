'''
Building a job's Python packages into a derived image (implementation-notes §L).

``python -m siliconcompiler.remote.server.packages.envbuild <workspace>/spec.json``
runs as its own job on the builder queue while the job stages, and always
writes ``<workspace>/result.json``, all the API reads.

🔴 Isolated, every part load-bearing (contract item 3): pip runs inside the base
image, under the node's Python; in its own container with a read-only root, a
private /tmp and none of the base's bind mounts (no PDK, build tree or cluster
socket); with only a loopback and a unix socket to a proxy admitting the
`index_allowlist` hosts, never a non-public address; from the deployment's
`package_indexes` only. So a source build's code runs with nothing to reach.
⚠️ The proxy sees an HTTPS host, not a path: an https entry admits its host.
'''

import copy
import http
import http.server
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
from typing import Any, Dict, List, Optional
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
    # Atomically: the API polls for it.
    from siliconcompiler.remote.server.running.runspec import write_json

    write_json(workspace / RESULT, result)
    print(json.dumps(result, indent=1))
    return 0


def build(spec: Dict[str, Any], workspace: Path, run=None) -> Dict[str, Any]:
    '''Build one environment into a derived image; returns the result record.

    ``run`` starts the build container and waits (default `_run_container`).
    '''
    from siliconcompiler.remote.environment import IMAGE_SITE
    from siliconcompiler.remote.server.packages import pipbuild
    from siliconcompiler.remote.server.software import images, oci

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

    # A unix socket's path is bounded (108 bytes), so a short directory.
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
        # Source builds only if the operator allows, and only here (surface D291).
        for index in spec.get("indexes") or []:
            command += ["--index-url", index]
        if spec.get("source_builds"):
            command.append("--allow-source")
        config = build_config(base_spec, base, req, out, sockets, command)
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
             "platform": pip.get("platform"), "ignored": pip.get("ignored") or {},
             "yanked": pip.get("yanked") or []}
    if pip.get("absent") or pip.get("source_only"):
        # Not listed, or source only: the job is sent back for the client's wheel.
        return {"ok": False, "reason": "absent", **facts,
                "absent": pip.get("absent") or [],
                "source_only": pip.get("source_only") or [],
                "tail": pip.get("tail", "")}
    if pip.get("returncode") != 0:
        # 🔴 A refused host is policy; an unanswering network is the server's failure.
        if pip.get("network") and not proxy.refused:
            return {"ok": False, "reason": "error", **facts,
                    "detail": "the build could not reach an index:\n" + pip.get("tail", "")}
        return {"ok": False, "reason": "uninstallable", **facts,
                "unresolved": pip.get("unresolved") or [], "refused": proxy.refused,
                "only_source": pip.get("only_source") or [],
                "tail": pip.get("tail", "")}

    site = out / "site"
    site.mkdir(exist_ok=True)
    layer = oci.layer_from(site, IMAGE_SITE)
    ref, digest = oci.derive(spec["base_ref"], layer,
                             comment=spec.get("comment") or "sc-server environment")
    images.stage_derived_bundle(root, spec["base_digest"], digest, site)
    shutil.rmtree(out, ignore_errors=True)
    return {"ok": True, "ref": ref, "digest": digest,
            "installed": pip.get("installed") or [],
            "substituted": pip.get("substituted") or {}, **facts}


def build_config(base: Dict[str, Any], bundle: Path, req: Path, out: Path,
                 sockets: Path, command: List[str]) -> Dict[str, Any]:
    '''The build container's OCI configuration, from its base image's staged ``bundle``.'''
    from siliconcompiler.remote.server.software.images import (
        _borrowed_root, _is_bind, drop_capabilities)

    spec = copy.deepcopy(base)
    spec["root"] = _borrowed_root(base, bundle, readonly=True)
    spec["hostname"] = "sc-envbuild"

    drop_capabilities(spec)
    process = spec.setdefault("process", {})
    process["terminal"] = False
    process["cwd"] = "/tmp"
    process["args"] = list(command)
    process["env"] = [f"PATH={_image_path(base)}", "HOME=/tmp", "LANG=C.UTF-8",
                      "PYTHONNOUSERSITE=1"]

    kept = []
    for mount in spec.get("mounts") or []:
        if _is_bind(mount):
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
    '''Start the build container, by ``srun --container`` or else crun; returns its output.'''
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


class Proxy:
    '''An HTTP proxy on a unix socket that admits an allowlist, and nothing else.

    ``CONNECT`` is checked by host and port, a plain http ``GET``/``HEAD`` by
    whole URL. 🔴 Never to a non-public address, but for the builder's
    ``private_exact_hosts`` (surface D172): an exact-host index entry may be the
    operator's own mirror; a wildcard never. Past ``max_bytes`` relayed back,
    the connection is cut and ``oversize`` set.
    '''

    def __init__(self, address, entries, private_exact_hosts: bool = False,
                 max_bytes: Optional[int] = None):
        import socketserver

        from siliconcompiler.remote.server.staging import allowlist

        self._rules = [allowlist.parse(entry) for entry in entries]
        self._hosts = [rule._replace(segments=()) for rule in self._rules
                       if rule.scheme == "https"]
        self._private_exact = private_exact_hosts
        self.refused: List[str] = []
        self._max_bytes = max_bytes
        self._received = 0
        self._counting = threading.Lock()
        self.oversize = False

        base = socketserver.ThreadingUnixStreamServer
        server = type("_ProxyServer", (base,), {
            "daemon_threads": True, "block_on_close": False, "request_queue_size": 64})
        self._server = server(address, _ProxyHandler)
        self._server.proxy = self
        self._serving = None

    def start(self) -> None:
        self._serving = threading.Thread(target=self._server.serve_forever, daemon=True,
                                         name="envbuild-proxy")
        self._serving.start()

    def close(self) -> None:
        # `shutdown` waits for `serve_forever` to stop, so only once it ran.
        if self._serving is not None:
            self._server.shutdown()
        self._server.server_close()

    def admits_connect(self, host: str, port: int) -> bool:
        return self._matching(self._hosts, f"https://{host}:{port}/") is not None

    def admits_get(self, url: str) -> bool:
        return urlsplit(url).scheme == "http" and \
            self._matching(self._rules, url) is not None

    @staticmethod
    def _matching(rules, url: str):
        from siliconcompiler.remote.server.staging import allowlist

        for rule in rules:
            if allowlist.allows([rule], url):
                return rule
        return None

    def _relayed(self, size: int) -> bool:
        '''Count ``size`` bytes relayed back; False once past ``max_bytes``.'''
        if self._max_bytes is None:
            return True
        with self._counting:
            self._received += size
            if self._received > self._max_bytes:
                self.oversize = True
            return not self.oversize

    def _public_only(self, rules, url: str) -> bool:
        '''Whether the address rule binds this connection.'''
        rule = self._matching(rules, url)
        return not (self._private_exact and rule is not None
                    and not rule.host.startswith("*."))


class _ProxyHandler(http.server.BaseHTTPRequestHandler):
    '''One connection to the proxy: a tunnel, or one plain GET or HEAD.'''

    protocol_version = "HTTP/1.1"
    # 🔴 Unbuffered, so a pipelined TLS hello stays on the socket for the tunnel.
    rbufsize = 0

    def do_CONNECT(self) -> None:
        proxy = self.server.proxy
        host, _, port = self.path.rpartition(":")
        host = host.strip("[]").lower()
        if not port.isdigit() or not proxy.admits_connect(host, int(port)):
            return self._refuse(host)
        upstream = _open_public(host, int(port), public_only=proxy._public_only(
            proxy._hosts, f"https://{host}:{port}/"))
        if upstream is None:
            return self._refuse(host, "resolves to a non-public address")
        with upstream:
            self.send_response(200, "Connection established")
            self.end_headers()
            self._splice(upstream)

    def do_GET(self) -> None:
        proxy = self.server.proxy
        if not self.path.startswith("http://"):
            return self._answer(405, "CONNECT, or GET and HEAD for http")
        parts = urlsplit(self.path)
        if not proxy.admits_get(self.path):
            return self._refuse((parts.hostname or "").lower())
        upstream = _open_public(parts.hostname, parts.port or 80,
                                public_only=proxy._public_only(proxy._rules, self.path))
        if upstream is None:
            return self._refuse(parts.hostname, "resolves to a non-public address")
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        kept = [f"{name}: {value}" for name, value in self.headers.items()
                if not name.lower().startswith("proxy-") and name.lower() != "connection"]
        with upstream:
            head = [f"{self.command} {path} HTTP/1.1", *kept, "Connection: close", "", ""]
            upstream.sendall("\r\n".join(head).encode("latin-1"))
            self._splice(upstream)

    do_HEAD = do_GET

    def __getattr__(self, name):
        # Every other method: 405, where `http.server` would answer 501.
        if name.startswith("do_"):
            return lambda: self._answer(405, "CONNECT, or GET and HEAD for http")
        raise AttributeError(name)

    def _splice(self, upstream) -> None:
        self.close_connection = True
        _splice(self.connection, upstream, self.server.proxy._relayed)

    def _refuse(self, host: str, why: str = "is not on the allowlist") -> None:
        refused = self.server.proxy.refused
        if host and host not in refused:
            refused.append(host)
        print(f"proxy: refused {host}: it {why}", flush=True)
        self._answer(403, f"{host} {why}")

    def _answer(self, status: int, why: str) -> None:
        # One write, so the reason is never a body still in flight.
        body = f"{why}\n".encode()
        self.close_connection = True
        self.wfile.write(f"{self.protocol_version} {status} {http.HTTPStatus(status).phrase}\r\n"
                         f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
                         .encode("latin-1") + body)

    def log_message(self, format, *args) -> None:
        return


def _open_public(host: str, port: int, public_only: bool = True):
    '''Connect to ``host`` if all its addresses are public: to one of those checked,
    never a second lookup.'''
    from siliconcompiler.remote.server.staging.allowlist import _all_public

    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return None
    if public_only and not _all_public(infos):
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


def _splice(one, other, relayed=None) -> None:
    '''Relay both ways until both ends close; ``relayed`` returning False stops it.'''
    def pipe(source, sink, count=None):
        try:
            while True:
                data = source.recv(65536)
                if not data or (count is not None and not count(len(data))):
                    break
                sink.sendall(data)
        except OSError:
            pass
        finally:
            try:
                sink.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    back = threading.Thread(target=pipe, args=(other, one, relayed), daemon=True)
    back.start()
    pipe(one, other)
    back.join()


def wait_for(workspace: Path, timeout: float, alive=None, pause: float = 2.0,
             ask_every: float = 30.0, grace: float = 15.0):
    '''A build's result once written; None past ``timeout`` or ``grace`` after the job is gone.

    The grace is for a shared filesystem, where the file can appear after its
    writer ended; the scheduler is asked at most every ``ask_every``.
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
