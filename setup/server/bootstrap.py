#!/venv/bin/python3
'''Everything a fresh deployment needs, before the server will start.

A one-shot compose service ``scserver`` waits on: it leaves a populated
registry, a staged bundle per image, and a ``config.json`` saying jobs run in
containers. A service, not a script to remember: ``containers: true`` with an
empty registry refuses to start, so as two commands it deadlocked.

The one privilege this stack takes: the docker socket, in this container
only, for two calls (tag and push), to get the built images into a registry.
A registry because a locally built image has no repository digest, and the
digest is what is approved and run. Two names for it: the host's daemon
pushes to ``localhost:5000``, the cluster pulls (and registers) ``registry:5000``.
'''

import base64
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse

from http.client import HTTPConnection
from pathlib import Path


# The daemon's names for the images compose just built.
STACK_IMAGE = os.environ.get("SC_STACK_IMAGE", "sc-server-slurm-sctools")
RUNTIME_IMAGE = os.environ.get("SC_RUNTIME_IMAGE", "sc-server-slurm-scruntime")

# Where the DAEMON pushes, and where the CLUSTER pulls. See the module note.
PUSH_TO = os.environ.get("SC_PUSH_REGISTRY", "localhost:5000")
PULL_FROM = os.environ.get("SC_PULL_REGISTRY", "registry:5000")

# The interpreter inside the images, not this one.
PYTHON = os.environ.get("SC_IMAGE_PYTHON", "python3")

DATADIR = Path(os.environ.get("SC_DATADIR", "/sc_server"))
DOCKER_SOCK = os.environ.get("SC_DOCKER_SOCKET", "/var/run/docker.sock")

# Every tool SiliconCompiler can drive, and its driver module, spelled out.
# No convention to fall back on: `kepler-formal` is `tools.keplerformal`.
DRIVERS = {
    "bambu": "siliconcompiler.tools.bambu.convert",
    "bluespec": "siliconcompiler.tools.bluespec.convert",
    "chisel": "siliconcompiler.tools.chisel.convert",
    "genfasm": "siliconcompiler.tools.genfasm.bitstream",
    "ghdl": "siliconcompiler.tools.ghdl.convert",
    "graphviz": "siliconcompiler.tools.graphviz",
    "gtkwave": "siliconcompiler.tools.gtkwave.show",
    "icarus": "siliconcompiler.tools.icarus",
    "icepack": "siliconcompiler.tools.icepack.bitstream",
    "kepler-formal": "siliconcompiler.tools.keplerformal",
    "klayout": "siliconcompiler.tools.klayout",
    "magic": "siliconcompiler.tools.magic",
    "mlir": "siliconcompiler.tools.mlir",
    "montage": "siliconcompiler.tools.montage",
    "netgen": "siliconcompiler.tools.netgen.lvs",
    "nextpnr": "siliconcompiler.tools.nextpnr.apr",
    "openroad": "siliconcompiler.tools.openroad",
    "opensta": "siliconcompiler.tools.opensta",
    "sby": "siliconcompiler.tools.sby",
    "slang": "siliconcompiler.tools.slang",
    "soda": "siliconcompiler.tools.soda",
    "surelog": "siliconcompiler.tools.surelog.parse",
    "surfer": "siliconcompiler.tools.surfer.show",
    "sv2v": "siliconcompiler.tools.sv2v.convert",
    "vcd2fst": "siliconcompiler.tools.vcd2fst.convert",
    "verilator": "siliconcompiler.tools.verilator",
    "vpr": "siliconcompiler.tools.vpr",
    "xdm": "siliconcompiler.tools.xdm.convert",
    "xyce": "siliconcompiler.tools.xyce.simulate",
    "yosys": "siliconcompiler.tools.yosys",
}

# Driven but deliberately not published: named, so a test can tell a tool
# forgotten here from one left out on purpose.
NOT_PUBLISHED = {"vivado"}

# `builtin` and `execute` are in neither: their `_remote_toolname` is None.
TOOLS = sorted(DRIVERS)

# Tools whose version is a Python distribution (`version_package`): slang's
# driver runs pyslang in-process. A wrapper still needs its program, so the
# Dockerfile installs `dot` for graphviz; the probe does not check it.
AS_DISTRIBUTION = {"slang": "pyslang", "graphviz": "graphviz"}

# Distributions a node's SiliconCompiler process needs, at SiliconCompiler's range.
FRAMEWORK = ("cocotb",)

# What the tools image must hold: a missing one refuses the registration as a
# broken image, where any other catalogue tool is merely not offered.
EXPECTED = (os.environ.get("SC_TOOLS")
            or "klayout openroad opensta yosys vpr icarus verilator bambu "
               "soda mlir slang").split()

# What a framework image needs to submit nodes: munge's socket, slurm.conf, and
# resolv.conf, which Slurm does not carry over, or slurmctld will not resolve
# ("Unable to contact slurm controller").
MOUNTS = ["/run/munge", "/sc_tools/etc", "/etc/resolv.conf"]

# The orchestrator's own partition, so coordinators never fill the compute slots.
BATCH_QUEUE = os.environ.get("SC_BATCH_QUEUE", "coordinate")

# The builder's own partition, so a burst of builds waits away from flows.
BUILD_QUEUE = os.environ.get("SC_BUILD_QUEUE", "build")

# Loopback: where compose publishes the API and the portal.
WEB_URL_BASE = os.environ.get("SC_WEB_URL_BASE", "http://localhost:8080")


# "local: digest: sha256:<hex> size: 856", the daemon's final push line.
_DIGEST_IN_STATUS = re.compile(r"digest:\s*(sha256:[0-9a-f]{64})")


def say(message: str) -> None:
    print(f"| bootstrap | {message}", flush=True)


class _Daemon(HTTPConnection):
    '''The Engine API over its unix socket.

    Not `skopeo docker-daemon:`, which exports gigabytes to compute a
    manifest, nor the `docker` CLI, a package needed for nothing else.
    '''

    def __init__(self, path: str):
        super().__init__("localhost")
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(1800)
        self.sock.connect(self._path)


def _post(path: str, headers=None):
    '''One POST, with the streamed body returned as a list of JSON objects.'''
    daemon = _Daemon(DOCKER_SOCK)
    try:
        daemon.request("POST", path, headers=headers or {})
        response = daemon.getresponse()
        body = response.read().decode("utf-8", "replace")
    finally:
        daemon.close()

    if response.status >= 400:
        raise RuntimeError(f"docker said {response.status} to {path}: {body}")

    events = []
    for line in body.splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


def _call(method: str, path: str, body=None, raw: bool = False,
          binary: bool = False, limit=None):
    '''One request to the daemon; returns parsed JSON, text, or raw bytes.

    Past ``limit`` is refused, not cut: it bounds what an image printed.
    '''
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if payload else {}

    daemon = _Daemon(DOCKER_SOCK)
    try:
        daemon.request(method, path, body=payload, headers=headers)
        response = daemon.getresponse()
        data = response.read() if limit is None else response.read(limit + 1)
    finally:
        daemon.close()

    if limit is not None and len(data) > limit:
        raise RuntimeError(f"{path} answered more than {limit} bytes")

    if response.status >= 400:
        raise RuntimeError(f"docker said {response.status} to {path}: "
                           f"{data.decode('utf-8', 'replace')}")
    if binary:
        return data

    text = data.decode("utf-8", "replace")
    return text if raw else (json.loads(text) if text.strip() else {})


def _get(path: str):
    '''One GET, as parsed JSON.'''
    return _call("GET", path)


def run_in(image: str, command) -> str:
    '''Run one command inside an image and return what it printed.

    The only way to know what is in an image is to ask it from inside.
    '''
    from siliconcompiler.remote.server.software import probe

    created = _call("POST", "/containers/create",
                    # `Entrypoint: []`, or Cmd becomes arguments to the
                    # image's ENTRYPOINT and the probe reports nothing.
                    # No TTY: on a terminal tools colour and wrap their output
                    # (klayout's colour once hid a frame's closing marker).
                    {"Image": image, "Entrypoint": [], "Cmd": list(command),
                     "Tty": False, "NetworkDisabled": True})
    container = created["Id"]
    try:
        _call("POST", f"/containers/{container}/start")
        _call("POST", f"/containers/{container}/wait")
        # Bounded, on a host with the docker socket; doubled for the framing.
        return _demux(_call("GET",
                            f"/containers/{container}/logs?stdout=1&stderr=1",
                            raw=True, binary=True, limit=2 * probe.MAX_OUTPUT))
    finally:
        _call("DELETE", f"/containers/{container}?force=1")


def _demux(stream: bytes) -> str:
    """Docker's multiplexed log stream (8-byte header per write), as text."""
    out, at = [], 0
    while at + 8 <= len(stream):
        size = int.from_bytes(stream[at + 4:at + 8], "big")
        out.append(stream[at + 8:at + 8 + size])
        at += 8 + size

    if at < len(stream):
        # Not framed after all, as a TTY container returns.
        out.append(stream[at:])

    return b"".join(out).decode("utf-8", "replace")


def ask_image(image: str, python_names, tools) -> dict:
    '''What this image actually holds, by running the probe's script in it.

    ``tools`` maps each tool to its driver module, read here, where
    SiliconCompiler is. Never fatal: unknown versions have a spelling in
    the registry, and no deployment at all is worse.
    '''
    from siliconcompiler.remote.server.software import probe

    wanted = [(name, "python", None, None) for name in python_names]
    # The image's own Python (surface D293).
    wanted.append((probe.INTERPRETER, "interpreter", None, None))
    for name, driver in sorted(tools.items()):
        wanted.append((name, "tool", driver, AS_DISTRIBUTION.get(name)))

    try:
        output = run_in(image, ["sh", "-c", probe.script(wanted)])
    except Exception as e:                                       # noqa: BLE001
        say(f"could not probe {image}: {e}")
        return {}

    try:
        return probe.read_output(wanted, output)
    except Exception as e:                                       # noqa: BLE001
        say(f"could not read what {image} answered: {e}")
        return {}


def published_on(local: str) -> str:
    '''The day an image was built, as the `published_date` version of a tool reporting none.

    Never an invented number, which would read as reported. The image's
    creation date, not today's, so a re-run registers the same row.
    '''
    created = built_at(local)
    # "20260924": a bare integer compares as a version, 2026-09-24 does not.
    stamp = created[:10].replace("-", "")
    if len(stamp) != 8 or not stamp.isdigit():
        raise RuntimeError(f"the daemon reported no creation time for {local}: "
                           f"{created!r}")
    return stamp


def built_at(local: str) -> str:
    '''When the image was built, to the second.

    Not `published_on`'s date: this breaks ties between images, and two built
    on one day is ordinary.
    '''
    return _get(f"/images/{local}/json").get("Created") or ""


def content_of(local: str):
    '''The image's own manifest digest and platform, or ``(None, None)``.

    Stable across a no-op rebuild, unlike the ID: on the containerd store the
    ID is an index carrying BuildKit's timestamped attestation. Compose did
    not pass `provenance: false` through. None on the classic store, already stable.
    '''
    for manifest in _get(f"/images/{local}/json?manifests=1").get("Manifests") or []:
        if manifest.get("Kind") == "image":
            return (manifest["Descriptor"]["digest"],
                    (manifest.get("ImageData") or {}).get("Platform"))
    return None, None


def push(local: str, repository: str, tag: str) -> str:
    '''Put one locally built image in the registry; returns its digest.

    Tagged with its SiliconCompiler version, for the reader. Nothing
    resolves by tag: the digest is what is registered, staged and run.
    '''
    target = f"{PUSH_TO}/{repository}"

    say(f"pushing {local} to {target}:{tag}")
    _post(f"/images/{local}/tag?repo={target}&tag={tag}")

    # Only this platform's manifest, so the digest survives a no-op rebuild
    # (`content_of`).
    query = f"tag={tag}"
    _, platform = content_of(local)
    if platform:
        query += "&platform=" + urllib.parse.quote(json.dumps(platform))

    # The daemon requires the header even for a registry with no auth.
    events = _post(f"/images/{target}/push?{query}",
                   headers={"X-Registry-Auth": base64.urlsafe_b64encode(b"{}").decode()})

    digest = None
    for event in events:
        if event.get("error"):
            raise RuntimeError(f"pushing {target}: {event['error']}")

        # `aux` is documented, but some daemons send only the final status line.
        digest = (event.get("aux") or {}).get("Digest") or digest
        found = _DIGEST_IN_STATUS.search(event.get("status") or "")
        if found:
            digest = found.group(1)

    if not digest:
        raise RuntimeError(
            f"the daemon pushed {target} and reported no digest: "
            f"{events[-3:]}")
    return digest


def digest_of(local: str, repository: str):
    '''The digest this image registers as: its own manifest's, else its last push's, or None.'''
    digest, _ = content_of(local)
    return digest or pushed_as(local, repository)


def pushed_as(local: str, repository: str):
    '''The digest this exact image was pushed as, or None.

    From `RepoDigests`, not `Id`, which on the classic store is the config's digest.
    '''
    prefix = f"{PUSH_TO}/{repository}@"
    for ref in _get(f"/images/{local}/json").get("RepoDigests") or []:
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return None


def wait_for_registry() -> None:
    host, _, port = PULL_FROM.partition(":")
    for _ in range(120):
        try:
            with socket.create_connection((host, int(port or 5000)), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"timed out waiting for the registry at {PULL_FROM}")


def write_config() -> None:
    '''Write what this deployment is.

    Before staging: a bundle bakes in the mount list it was staged with.
    '''
    path = DATADIR / "config.json"
    DATADIR.mkdir(parents=True, exist_ok=True)

    config = {}
    if path.is_file():
        try:
            config = json.loads(path.read_text()) or {}
        except ValueError:
            say(f"{path} is not readable JSON; replacing it")

    config["containers"] = True
    config["container_mounts"] = MOUNTS
    config["batch_queue"] = BATCH_QUEUE
    # Advertises `python.env`: a node's Python is built into an image.
    config["env_builder"] = True
    config["build_queue"] = BUILD_QUEUE
    # A test rig, so it may reveal its layout in each node's record.
    config["track_provenance"] = True
    # A key an older bootstrap wrote.
    config.pop("portal_plaintext_peers", None)
    # Configured, never derived from a request header (config.py says why).
    config["web_url_base"] = WEB_URL_BASE
    config["public_origins"] = [WEB_URL_BASE, WEB_URL_BASE.replace("localhost", "127.0.0.1")]

    path.write_text(json.dumps(config, indent=2) + "\n")
    say(f"wrote {path}")


def registry(*args: str) -> None:
    '''One operator command, its own message left to speak for itself.

    Not `check=True`, whose traceback would bury what the child printed.
    '''
    done = subprocess.run(
        [sys.executable, "-m", "siliconcompiler.remote.server.software.registry",
         "-datadir", str(DATADIR), *args])
    if done.returncode:
        raise SystemExit(
            f"registry {' '.join(args)} failed; see the message above")


def _declare(tool: str, answer, published: str):
    """What one image should say it holds for one tool, as add-image arguments.

    The version read, else the publish date, marked. Only where the probe saw
    it present: an unchecked claim dispatches nodes into images without the tool.
    Never a variable named `version`, which shadowed `register`'s.
    """
    answer = answer or {}
    if answer.get("present") is not True:
        return []

    found = answer.get("version")
    if found:
        registry("add-version", tool, found)
        return ["-contains", f"{tool}=={found}"]

    registry("add-version", tool, published, "-unversioned")
    return ["-contains", f"{tool}=={published}"]


def _refuse_what_is_missing(image: str, held: dict) -> None:
    """Refuse the whole image where an `EXPECTED` tool tested absent.

    The whole image, not the row: the failure is cheapest here, before a node
    is placed in it and dies. Only a tested absence; untested or mute is fine.
    """
    missing = [tool for tool in EXPECTED
               if (held.get(tool) or {}).get("present") is False]
    if not missing:
        return

    raise SystemExit(
        f"{image} does not hold {', '.join(missing)}, and registering it would "
        "say it does -- a node would then be placed there, dispatched, and "
        "die with the rest of the run cancelled behind it. Fix the image, or "
        "take those out of SC_TOOLS.")


def say_what_it_holds(held: dict) -> None:
    """One line per tool that is there, with both numbers where they differ.

    A function, not a loop in `main`: a loop variable `version` twice
    shadowed the SiliconCompiler version and mis-tagged both images.
    """
    for tool in TOOLS:
        answer = held.get(tool) or {}
        found, reported = answer.get("version"), answer.get("reported")

        if answer.get("present") is False:
            continue
        if answer.get("unparsed"):
            # Said loudly: presence was right and the parse was not (gtkwave's
            # `initialize`), and nothing downstream can tell. Recorded as the
            # publish date, never rewritten.
            say(f"  {tool}: present, but {answer['unparsed']!r} is not a "
                f"version; recorded as the publish date -- check what `{tool}` "
                "prints without a terminal or a display")
        elif not found:
            say(f"  {tool}: present, no version reported")
        elif reported and reported != found:
            # verilator prints 5.052, stored as 5.52.
            say(f"  {tool}: {found}  (reported {reported})")
        else:
            say(f"  {tool}: {found}")


def register(version: str, tools_digest: str, runtime_digest: str,
             published: str, held: dict, runtime_held: dict) -> None:
    '''Put what the probe found into the registry.

    A version read is registered as reported, otherwise the publish date,
    marked (`images.matches`). Each image declares only what it answered for.
    '''
    _refuse_what_is_missing(STACK_IMAGE, held)

    registry("add-software", "siliconcompiler", "-kind", "python")
    registry("add-version", "siliconcompiler", version)

    contains, runtime_contains = [], []

    # Each image's own Python, matched by `requested_versions.interpreter`.
    from siliconcompiler.remote.server.software import probe
    registry("add-software", probe.INTERPRETER, "-kind", "interpreter")
    for answer, into in ((held, contains), (runtime_held, runtime_contains)):
        said = answer.get(probe.INTERPRETER) or {}
        if said.get("present") and said.get("version"):
            into += _declare(probe.INTERPRETER, said, published)

    # cocotb, named in a cocotb node's `requested_versions.python`.
    for name in FRAMEWORK:
        registry("add-software", name, "-kind", "python")
        contains += _declare(name, held.get(name), published)
        runtime_contains += _declare(name, runtime_held.get(name), published)
    for tool in TOOLS:
        add = ["add-software", tool, "-kind", "tool",
               "-driver", DRIVERS[tool]]
        if AS_DISTRIBUTION.get(tool):
            add += ["-version-package", AS_DISTRIBUTION[tool]]
        registry(*add)

        # Each image declares exactly what the probe found in it.
        contains += _declare(tool, held.get(tool), published)
        runtime_contains += _declare(tool, runtime_held.get(tool), published)

    say("staging bundles (skopeo, then umoci -- the big one takes a minute)")
    registry("add-image", f"{PULL_FROM}/sc-runtime:{version}",
             "-digest", runtime_digest, "-built", built_at(RUNTIME_IMAGE),
             "-contains", f"siliconcompiler=={version}", *runtime_contains,
             "-stage")
    registry("add-image", f"{PULL_FROM}/sc-tools:{version}",
             "-digest", tools_digest, "-built", built_at(STACK_IMAGE),
             "-contains", f"siliconcompiler=={version}", *contains, "-stage")


def already_registered(version: str) -> bool:
    '''Whether both images are live in the store, at this version and digest, and staged.

    Asked of the store, never a marker file that a reset store would contradict.
    The manifest digest (`content_of`) is the whole test: it changes exactly
    when the image does.
    '''
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.state.store import Store, StoreVersionError

    wanted = {
        f"{PULL_FROM}/sc-runtime:{version}": digest_of(RUNTIME_IMAGE, "sc-runtime"),
        f"{PULL_FROM}/sc-tools:{version}": digest_of(STACK_IMAGE, "sc-tools")}
    database = DATADIR / "server.db"
    if not all(wanted.values()) or not database.is_file():
        return False

    try:
        with Store(database) as store:
            live = {row["registry_ref"]: row["digest"]
                    for row in images.live_images(store)}
    except StoreVersionError:
        # Registering explains what to do about an unreadable store.
        return False

    return all(
        live.get(ref) == digest
        and images.is_staged(images.bundle_path(DATADIR / "images", digest))
        for ref, digest in wanted.items())


def main() -> int:
    import siliconcompiler

    version = siliconcompiler.__version__

    wait_for_registry()
    # Every time, before the check: settings change without the images.
    write_config()

    # Or every `compose up` re-probes, re-pushes and re-registers both.
    if already_registered(version):
        say(f"siliconcompiler {version} is already registered at these "
            "digests; nothing to do")
        return 0

    # A rebuild at the same version supersedes the old image; at a new one
    # both stay live. Read off the local image, before the push.
    published = published_on(STACK_IMAGE)

    say("asking the tools image what it actually holds")
    held = ask_image(STACK_IMAGE, ["siliconcompiler", *FRAMEWORK], DRIVERS)
    say_what_it_holds(held)

    # Asked too: it carries what arrives with siliconcompiler (`slang`).
    say("asking the runtime image the same")
    runtime_held = ask_image(RUNTIME_IMAGE, ["siliconcompiler", *FRAMEWORK], DRIVERS)
    for tool in TOOLS:
        found = (runtime_held.get(tool) or {}).get("version")
        if found:
            say(f"  {tool}: {found}")

    runtime_digest = push(RUNTIME_IMAGE, "sc-runtime", version)
    tools_digest = push(STACK_IMAGE, "sc-tools", version)

    register(version, tools_digest, runtime_digest, published, held,
             runtime_held)

    say(f"this deployment runs siliconcompiler {version} in containers")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:                                       # noqa: BLE001
        # As `registry`: this output is what somebody reads when compose stops.
        say(f"failed: {e}")
        sys.exit(1)
