#!/venv/bin/python3
'''Everything a fresh deployment needs, before the server will start.

``docker compose up`` and nothing else. This runs as a one-shot service that
``scserver`` waits on, so by the time the server starts there is a populated
registry, a staged bundle for every image, and a ``config.json`` that says this
deployment runs jobs in containers.

🔴 **It is a service rather than a script you remember to run, and that is the
whole point.** A deployment with ``containers: true`` and an empty registry
refuses to start -- correctly, because nothing on it could be dispatched -- so
the moment the registration is needed is the moment there is no server to run
it through. As two commands that was a deadlock the first time somebody reset
the store. As a dependency it cannot happen: compose will not start the server
until this has exited 0.

⚠️ **The one privilege this stack takes: the docker socket, in this container
only, for as long as it runs.** Two images have to get from the daemon that
just built them into the registry, and the daemon is the only thing that knows
their layers. It is used for exactly two calls -- tag and push -- and nothing
else in the stack can see it. The compute nodes deliberately cannot: they run
containers through ``crun``, which is a binary Slurm execs.

🔴 **Why a registry at all, when the images are right there in the daemon:** a
locally built image has no repository digest. The digest is what an operator
approves and what actually runs two months later, so registering an image that
has none is refused rather than recorded as something it is not.

⚠️ **Two spellings of one registry, and they are not interchangeable.** The
host's daemon does the push and cannot resolve a compose service name, so it
pushes to the published ``localhost:5000``. The cluster pulls over the compose
network as ``registry:5000``, which is what gets registered. One registry, one
digest, two names for it.
'''

import base64
import json
import os
import re
import socket
import subprocess
import sys
import time

from http.client import HTTPConnection
from pathlib import Path


# What the daemon calls the images compose just built, and what they are called
# once they are in the registry.
STACK_IMAGE = os.environ.get("SC_STACK_IMAGE", "sc-server-slurm:local")
RUNTIME_IMAGE = os.environ.get("SC_RUNTIME_IMAGE", "sc-runtime:local")

# Where the DAEMON pushes, and where the CLUSTER pulls. See the module note.
PUSH_TO = os.environ.get("SC_PUSH_REGISTRY", "localhost:5000")
PULL_FROM = os.environ.get("SC_PULL_REGISTRY", "registry:5000")

# The interpreter INSIDE the images, which is not this one. Overridable
# because an image that puts SiliconCompiler in a venv has it somewhere else,
# and the probe is only useful if it can be started.
PYTHON = os.environ.get("SC_IMAGE_PYTHON", "python3")

DATADIR = Path(os.environ.get("SC_DATADIR", "/sc_server"))
DOCKER_SOCK = os.environ.get("SC_DOCKER_SOCKET", "/var/run/docker.sock")

# 🔴 Every tool a flow might reach for has to be declared, and this list is the
# sharpest edge in the file. A tool that is in the image and not in the
# registry raises no requirement, so its node resolves to the framework image
# and fails inside a container that never had it. These are what asicflow
# needs.
TOOLS = (os.environ.get("SC_TOOLS")
         or "klayout openroad opensta yosys vpr icarus verilator bambu soda "
            "mlir slang").split()

# 🔴 Tools whose version is a PYTHON DISTRIBUTION rather than a program.
# `slang` is the case: its driver runs pyslang in SiliconCompiler's own
# process, so there is no executable to ask and no `exe` on the task -- and the
# distribution is not called what the tool is called, which is why this is a
# map and not a rule.
#
# ⚠️ It is still registered as a TOOL, because that is what it is to a flow: a
# node names `slang` and has to be placed in an image holding it. The
# difference is only how its version is read.
#
# ⚠️ And it is in BOTH images, because it arrives with siliconcompiler rather
# than with the EDA stack. A tool declared only by the big image would drag
# every node that touches it into twelve gigabytes for no reason.
AS_DISTRIBUTION = {"slang": "pyslang"}

# What a container has to see beyond the data directory, which the staging code
# always mounts. A framework image submits every node of the flow it drives, so
# it needs all three:
#
#   /run/munge        the socket slurmctld authenticates it through
#   /sc_tools/etc     where slurm.conf lives
#   /etc/resolv.conf  🔴 or it cannot RESOLVE slurmctld. Slurm builds its own
#                     runtime spec from the bundle's and does not carry over
#                     the resolv.conf bind an unpacked image has, so the
#                     container gets the image's own -- empty, on a bare
#                     Ubuntu. The failure is "Unable to contact slurm
#                     controller (connect failure)", which reads like the
#                     controller being down.
MOUNTS = ["/run/munge", "/sc_tools/etc", "/etc/resolv.conf"]

# The partition the run's orchestrating process goes to. It computes nothing
# and would otherwise hold a compute slot for the length of the flow, so a wide
# run could fill the cluster with coordinators and leave nothing to run the
# nodes on. See the two partitions in slurm.conf.
BATCH_QUEUE = os.environ.get("SC_BATCH_QUEUE", "coordinate")

# The origin this stack publishes to a person. Loopback, because that is where
# the compose file publishes the API and the portal and nowhere else is
# reachable anyway.
WEB_URL_BASE = os.environ.get("SC_WEB_URL_BASE", "http://localhost:8080")


# "local: digest: sha256:<hex> size: 856", the daemon's final push line.
_DIGEST_IN_STATUS = re.compile(r"digest:\s*(sha256:[0-9a-f]{64})")


def say(message: str) -> None:
    print(f"| bootstrap | {message}", flush=True)


######################################################################
# The docker socket, for exactly two calls
######################################################################

class _Daemon(HTTPConnection):
    '''The Engine API over its unix socket.

    ⚠️ Deliberately not the `docker` CLI and not `skopeo docker-daemon:`. The
    CLI is a package this image has no other use for, and skopeo's daemon
    transport EXPORTS the whole image to compute its manifest -- minutes, every
    time, for six and a half gigabytes. Asking the daemon to push means the
    daemon uses what it already knows about the layers, which is the same work
    `docker push` does and the same speed.
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
          binary: bool = False):
    '''One request to the daemon. Returns parsed JSON, text, or raw bytes.'''
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if payload else {}

    daemon = _Daemon(DOCKER_SOCK)
    try:
        daemon.request(method, path, body=payload, headers=headers)
        response = daemon.getresponse()
        data = response.read()
    finally:
        daemon.close()

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

    🔴 **The only way to find out what is in an image is to ask it from
    inside.** Everything else -- the tag, the label, what somebody typed at
    registration -- is a claim about the image rather than the image.

    ⚠️ `Tty: true` so the output arrives as one stream rather than docker's
    multiplexed frames. It merges stderr into stdout, which is exactly why the
    probe prints behind a marker: a tool that writes a banner while being asked
    its version lands in the same stream as the answer.
    '''
    created = _call("POST", "/containers/create",
                    # 🔴 `Entrypoint: []` and not just `Cmd`. These images have
                    # an ENTRYPOINT, so a Cmd on its own becomes ARGUMENTS to
                    # it: the command never runs, the entrypoint does something
                    # else entirely, and the probe reports nothing for every
                    # tool -- which reads exactly like an image that holds
                    # none of them.
                    #
                    # 🔴 **No TTY, and that is not a preference.** A tool that
                    # thinks it is on a terminal behaves differently: klayout
                    # wraps its version in ANSI colour, which put an escape
                    # sequence in front of the marker ending its frame, so the
                    # frame never closed and a tool that had answered was
                    # recorded as absent. Others wrap their output to 80
                    # columns. Asking a program what version it is should not
                    # be a question about the terminal.
                    {"Image": image, "Entrypoint": [], "Cmd": list(command),
                     "Tty": False, "NetworkDisabled": True})
    container = created["Id"]
    try:
        _call("POST", f"/containers/{container}/start")
        _call("POST", f"/containers/{container}/wait")
        return _demux(_call("GET",
                            f"/containers/{container}/logs?stdout=1&stderr=1",
                            raw=True, binary=True))
    finally:
        _call("DELETE", f"/containers/{container}?force=1")


def _demux(stream: bytes) -> str:
    """Docker's multiplexed log stream, as text.

    Without a TTY the daemon frames every write: eight bytes of header --
    which stream it was, then the length -- and then that many bytes. Reading
    it as plain text leaves the headers in the output, and a header's length
    bytes are arbitrary, so one of them lands in the middle of a line often
    enough to matter.
    """
    out, at = [], 0
    while at + 8 <= len(stream):
        size = int.from_bytes(stream[at + 4:at + 8], "big")
        out.append(stream[at + 8:at + 8 + size])
        at += 8 + size

    if at < len(stream):
        # Not framed after all, which is what a TTY container returns. Taking
        # the rest verbatim is right for that and harmless otherwise.
        out.append(stream[at:])

    return b"".join(out).decode("utf-8", "replace")


def ask_image(image: str, python_names, tools) -> dict:
    '''What this image actually holds, by running the probe's script in it.

    🔴 **The script runs in the image and the PARSING happens here**, which is
    what lets any tools image be registered. An earlier version ran the probe
    module inside the image, and that works only where SiliconCompiler is
    installed -- which `ghcr.io/siliconcompiler/sc_tools` is not: it is the
    image SC's own CI runs tools in, and CI installs the framework into it at
    test time. Requiring the framework in every image an operator wants to
    register is requiring them to rebuild somebody else's image.

    ``tools`` maps a tool name to the module carrying its Task driver, which is
    what makes the command: the driver can live in any package, and this
    process is the one with SiliconCompiler in it.

    ⚠️ **Never fatal.** A probe that cannot run leaves every version unknown,
    and unknown is a state the registry has a spelling for. Refusing to
    bootstrap because a version could not be read would trade a complete
    catalogue for no deployment at all.
    '''
    from siliconcompiler.remote.server import probe

    wanted = [(name, "python", None) for name in python_names]
    # ⚠️ A tool whose version is a distribution is asked the python way, under
    # the distribution's name, and the answer is put back under the TOOL's --
    # `slang` is registered as slang and read as pyslang.
    back = {}
    for name, driver in sorted(tools.items()):
        distribution = AS_DISTRIBUTION.get(name)
        if distribution:
            wanted.append((distribution, "python", None))
            back[distribution] = name
        else:
            wanted.append((name, "tool", driver))

    try:
        output = run_in(image, ["sh", "-c", probe.script(wanted)])
    except Exception as e:                                       # noqa: BLE001
        say(f"could not probe {image}: {e}")
        return {}

    try:
        found = probe.read_output(wanted, output)
    except Exception as e:                                       # noqa: BLE001
        say(f"could not read what {image} answered: {e}")
        return {}

    for distribution, name in back.items():
        answer = found.pop(distribution, None)
        if answer:
            # Recorded as a tool, whatever it was read as.
            found[name] = {**answer, "kind": "tool"}
    return found


def published_on(local: str) -> str:
    '''The day an image was built. A version for the tools that report none,
    and the image's own `built_at`.

    🔴 **The honest answer to *which version of OpenROAD is in here*, which is
    that nobody asked it.** This bootstrap does not run the tools, so it cannot
    report their versions -- and recording them at the SiliconCompiler version,
    which is what it used to do, was inventing a number. That number then
    looked exactly like a reported one: a client asking for `openroad>=2.0`
    would have been matched against `0.38.9` and refused for a reason that was
    not true.

    So the tools are registered with the date the image was published and
    marked `published_date`, which is the mark that exists for this: they are
    listed, they satisfy a requirement that names no version -- the only kind
    SiliconCompiler generates -- and they can never satisfy a range.

    ⚠️ The image's own creation time and not today's date, so re-running this
    against the same image registers the same row rather than a new one every
    day.
    '''
    created = built_at(local)
    # "2026-09-24T10:11:12.345678901Z" -> "20260924". A bare integer, because a
    # version is compared as a version and 2026-09-24 is not one.
    stamp = created[:10].replace("-", "")
    if len(stamp) != 8 or not stamp.isdigit():
        raise RuntimeError(f"the daemon reported no creation time for {local}: "
                           f"{created!r}")
    return stamp


def built_at(local: str) -> str:
    '''When the image was built, to the second.

    🔴 **Not the date `published_on` returns, and the two are not the same
    thing.** That one is a VERSION for a tool that reports none, so it has to
    be a number that compares as a version. This one breaks the tie between
    two images carrying identical versions -- and two images built on the same
    day is the ordinary case, not the rare one, so a date cannot break it.
    '''
    return _get(f"/images/{local}/json").get("Created") or ""


def push(local: str, repository: str, tag: str) -> str:
    '''Put one locally built image in the registry. Returns its digest.

    🔴 Tagged with the SiliconCompiler version it holds, not `:local`. The tag
    is what a person reads in `sinfo`-adjacent places, in the images screen and
    in the bundle path, and `:local` says only *somebody built this here* --
    which is true of every image in the registry and distinguishes none of
    them. `registry:5000/sc-tools:0.38.9` says what is in it.

    ⚠️ It does not REPLACE the digest, and nothing resolves by tag: the digest
    is still what gets registered, staged and run, because a tag can be moved
    and a digest cannot. The tag is for the reader.
    '''
    target = f"{PUSH_TO}/{repository}"

    say(f"pushing {local} to {target}:{tag}")
    _post(f"/images/{local}/tag?repo={target}&tag={tag}")

    # An empty credential, which the daemon requires the header for even where
    # the registry wants no authentication at all.
    events = _post(f"/images/{target}/push?tag={tag}",
                   headers={"X-Registry-Auth": base64.urlsafe_b64encode(b"{}").decode()})

    digest = None
    for event in events:
        if event.get("error"):
            raise RuntimeError(f"pushing {target}: {event['error']}")

        # Two places, because the daemon reports it in whichever it feels like.
        # `aux` is the documented one; what this machine's daemon actually
        # sends is a final status line reading
        # "local: digest: sha256:... size: 856", and a push that only looked at
        # `aux` failed on a push that had plainly succeeded.
        digest = (event.get("aux") or {}).get("Digest") or digest
        found = _DIGEST_IN_STATUS.search(event.get("status") or "")
        if found:
            digest = found.group(1)

    if not digest:
        raise RuntimeError(
            f"the daemon pushed {target} and reported no digest: "
            f"{events[-3:]}")
    return digest


######################################################################
# The steps
######################################################################

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
    '''What this deployment is, written before anything reads it.

    🔴 Before the staging, not after: an unpacked bundle carries its mount list
    in its own `config.json`, so staging with the wrong one produces a bundle
    that looks right and is missing whatever the cluster needed -- and the
    failure lands far away, as a node that cannot contact the controller.
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
    # Where a person reads about a job. Deployment config rather than anything
    # derived from a request header -- see config.py for why that distinction
    # is a security one and not a tidiness one.
    config["web_url_base"] = WEB_URL_BASE

    path.write_text(json.dumps(config, indent=2) + "\n")
    say(f"wrote {path}")


def registry(*args: str) -> None:
    '''One operator command, with its own message left to speak for itself.

    ⚠️ `check=True` raises a `CalledProcessError` whose traceback lands on top
    of whatever the child already printed -- so a store this server cannot
    speak, which prints exactly what to do about it, arrived as two stacked
    tracebacks with the useful sentence in the middle of the first.
    '''
    done = subprocess.run(
        [sys.executable, "-m", "siliconcompiler.remote.server.registry",
         "-datadir", str(DATADIR), *args])
    if done.returncode:
        raise SystemExit(
            f"registry {' '.join(args)} failed; see the message above")


def drivers_for(names) -> dict:
    '''Where each tool's Task driver lives, as this process can see it.

    ⚠️ **Worked out here and RECORDED, not worked out at probe time.** The
    probe runs in a different interpreter with different packages, so *where
    the driver is* has to be data by the time it is asked. This process is the
    one place that has both the tool list and a SiliconCompiler to look in.

    🔴 Found by what a class says it drives and never by a module path.
    `kepler-formal` is driven from `siliconcompiler.tools.keplerformal`, so the
    obvious convention is already wrong in this tree, never mind for a site
    library shipping its own.
    '''
    from siliconcompiler import Task

    def descendants(cls):
        for child in cls.__subclasses__():
            yield child
            yield from descendants(child)

    import importlib
    import pkgutil

    import siliconcompiler.tools

    for found in pkgutil.walk_packages(siliconcompiler.tools.__path__,
                                       prefix="siliconcompiler.tools."):
        try:
            importlib.import_module(found.name)
        except Exception:                                        # noqa: BLE001
            continue

    seen: dict = {}
    for task_cls in set(descendants(Task)):
        try:
            tool = task_cls().tool()
        except Exception:                                        # noqa: BLE001
            continue
        if tool in names and task_cls.__module__:
            seen.setdefault(tool, set()).add(task_cls.__module__)

    return {name: _common(seen.get(name, ())) for name in names}


def _common(modules) -> str:
    """The package every one of a tool's task classes lives under.

    🔴 **The common prefix and NOT the shallowest module**, which is what this
    did first and what silently cost `icarus` its version. Its classes are
    spread over `...tools.icarus.compile`, `...icarus.cocotb_exec` and more,
    with nothing in the package's own `__init__` -- so the shallowest was
    whichever task file sorted first, the probe imported that one module, and
    the class that actually sets the executable was in a different file it
    never looked at. Every tool reported a version except that one, which is
    the shape of a bug nobody notices.

    ⚠️ Falls back to the shortest module where the prefix collapses to
    something too general to import usefully -- two classes in unrelated trees
    share only `siliconcompiler`, and importing that drives nothing.
    """
    modules = sorted(modules)
    if not modules:
        return None
    if len(modules) == 1:
        return modules[0]

    parts = modules[0].split(".")
    for module in modules[1:]:
        other = module.split(".")
        keep = 0
        while keep < min(len(parts), len(other)) and parts[keep] == other[keep]:
            keep += 1
        parts = parts[:keep]

    prefix = ".".join(parts)
    return prefix if prefix.count(".") >= 2 else min(modules, key=len)


def say_what_it_holds(held: dict) -> None:
    """One line per tool, with both numbers where they differ.

    🔴 **A function and not a loop in `main`, and that is not style.** Twice
    now a loop variable named `version` has shadowed the SiliconCompiler
    version that `main` holds and `register` is given -- once here and once
    inside `register` -- and both times the result was two images tagged with
    whatever the LAST tool reported. The failure lands at server startup,
    which says it cannot read a version nobody asked it to run. A scope with
    nothing else in it cannot do that.
    """
    for tool in TOOLS:
        answer = held.get(tool) or {}
        found, reported = answer.get("version"), answer.get("reported")

        if not found:
            say(f"  {tool}: no version reported")
        elif reported and reported != found:
            # Both, because they differ for real tools and only one of them is
            # what the tool actually printed: verilator says 5.052 and PEP 440
            # makes that 5.52, and OpenROAD's own normaliser rewrites its
            # version wholesale.
            say(f"  {tool}: {found}  (reported {reported})")
        else:
            say(f"  {tool}: {found}")


def register(version: str, tools_digest: str, runtime_digest: str,
             published: str, held: dict, runtime_held: dict,
             drivers: dict) -> None:
    '''Put what the probe found into the registry.

    🔴 **A version the probe READ is registered as reported; one it could not
    is registered as the image's publish date and marked.** The difference is
    load-bearing: only a reported version can satisfy a range, and `20260924`
    beats `2.0.1` under every comparison there is, so an unmarked date would
    outrank every real release for ever.

    ⚠️ **Each image declares what IT answered for**, and the fallback belongs
    to the tools image alone. That one is built to contain the whole list, so a
    tool that said nothing is present and mute; the runtime image is built to
    contain none of them, and declaring a tool it does not hold would place
    nodes in an image that cannot run them.
    '''
    registry("add-software", "siliconcompiler", "-kind", "python")
    registry("add-version", "siliconcompiler", version)

    contains, runtime_contains = [], []
    for tool in TOOLS:
        driver = drivers.get(tool)
        add = ["add-software", tool, "-kind", "tool"]
        if driver:
            add += ["-driver", driver]
        registry(*add)

        # ⚠️ NOT `version`, which is the SiliconCompiler version this function
        # is about and is used again below. Binding a tool's version to that
        # name shadowed it, and both images were tagged with whatever the last
        # tool reported.
        #
        # The COMPARABLE one -- the driver's own normalisation, already
        # applied -- because that is what a version range is matched against.
        # What the tool printed went to the log.
        found = (held.get(tool) or {}).get("version")
        if found:
            registry("add-version", tool, found)
            contains += ["-contains", f"{tool}=={found}"]
        else:
            # In the tools image, listed, and nobody asked it what it was.
            registry("add-version", tool, published, "-unversioned")
            contains += ["-contains", f"{tool}=={published}"]

        # The runtime image declares a tool only where it answered for one.
        # `slang` is the case that exists: it arrives with siliconcompiler
        # rather than with the EDA stack, so it is in both.
        in_runtime = (runtime_held.get(tool) or {}).get("version")
        if in_runtime:
            registry("add-version", tool, in_runtime)
            runtime_contains += ["-contains", f"{tool}=={in_runtime}"]

    say("staging bundles (skopeo, then umoci -- the big one takes a minute)")
    registry("add-image", f"{PULL_FROM}/sc-runtime:{version}",
             "-digest", runtime_digest, "-built", built_at(RUNTIME_IMAGE),
             "-contains", f"siliconcompiler=={version}", *runtime_contains,
             "-stage")
    registry("add-image", f"{PULL_FROM}/sc-tools:{version}",
             "-digest", tools_digest, "-built", built_at(STACK_IMAGE),
             "-contains", f"siliconcompiler=={version}", *contains, "-stage")


def main() -> int:
    import siliconcompiler

    version = siliconcompiler.__version__

    wait_for_registry()
    write_config()

    # ⚠️ A rebuild at the SAME version supersedes the earlier one, because the
    # reference is identical and the digest is not -- which is what should
    # happen. A rebuild at a NEW version leaves the old reference live beside
    # it, which is also what should happen: they are different images and a
    # job that named the old one still can.
    # Read before the push, off the local image: the digest changes when it is
    # pushed and the creation time does not.
    published = published_on(STACK_IMAGE)

    drivers = drivers_for(TOOLS)
    missing = [tool for tool, driver in drivers.items() if not driver]
    if missing:
        say(f"no driver here for {', '.join(missing)}; their versions cannot "
            "be read and will be recorded as the image's publish date")

    say("asking the tools image what it actually holds")
    held = ask_image(STACK_IMAGE, ["siliconcompiler"], drivers)
    say_what_it_holds(held)

    # ⚠️ Asked too, and not assumed empty. It carries whatever arrives with
    # siliconcompiler -- `slang` does -- and a tool it holds and does not
    # declare is a node sent to the big image for nothing.
    say("asking the runtime image the same")
    runtime_held = ask_image(RUNTIME_IMAGE, ["siliconcompiler"], drivers)
    for tool in TOOLS:
        found = (runtime_held.get(tool) or {}).get("version")
        if found:
            say(f"  {tool}: {found}")

    runtime_digest = push(RUNTIME_IMAGE, "sc-runtime", version)
    tools_digest = push(STACK_IMAGE, "sc-tools", version)

    register(version, tools_digest, runtime_digest, published, held,
             runtime_held, drivers)

    say(f"this deployment runs siliconcompiler {version} in containers")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:                                       # noqa: BLE001
        # Same reason as `registry` above: this runs as a compose service, and
        # its output is what somebody reads when `docker compose up` stops.
        say(f"failed: {e}")
        sys.exit(1)
