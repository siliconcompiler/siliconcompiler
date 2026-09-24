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

DATADIR = Path(os.environ.get("SC_DATADIR", "/sc_server"))
DOCKER_SOCK = os.environ.get("SC_DOCKER_SOCKET", "/var/run/docker.sock")

# 🔴 Every tool a flow might reach for has to be declared, and this list is the
# sharpest edge in the file. A tool that is in the image and not in the
# registry raises no requirement, so its node resolves to the framework image
# and fails inside a container that never had it. These are what asicflow
# needs.
TOOLS = (os.environ.get("SC_TOOLS")
         or "klayout openroad opensta slang surelog yosys").split()

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


def _get(path: str):
    '''One GET, as parsed JSON.'''
    daemon = _Daemon(DOCKER_SOCK)
    try:
        daemon.request("GET", path)
        response = daemon.getresponse()
        body = response.read().decode("utf-8", "replace")
    finally:
        daemon.close()

    if response.status >= 400:
        raise RuntimeError(f"docker said {response.status} to {path}: {body}")
    return json.loads(body)


def published_on(local: str) -> str:
    '''The day an image was built, as a version for the tools inside it.

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
    created = _get(f"/images/{local}/json").get("Created") or ""
    # "2026-09-24T10:11:12.345678901Z" -> "20260924". A bare integer, because a
    # version is compared as a version and 2026-09-24 is not one.
    stamp = created[:10].replace("-", "")
    if len(stamp) != 8 or not stamp.isdigit():
        raise RuntimeError(f"the daemon reported no creation time for {local}: "
                           f"{created!r}")
    return stamp


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


def register(version: str, tools_digest: str, runtime_digest: str,
             published: str) -> None:
    registry("add-software", "siliconcompiler")
    registry("add-version", "siliconcompiler", version)

    # 🔴 The tools are registered with the date their image was published and
    # marked `published_date`, because this bootstrap does not run them and
    # therefore does not know their versions. See `published_on`: a made-up
    # number here is indistinguishable from a reported one, and the mark is
    # what keeps it from ever being matched against a range.
    #
    # A real deployment with a curated registry records real tool versions,
    # because there the operator is choosing between them.
    contains = []
    for tool in TOOLS:
        registry("add-software", tool)
        registry("add-version", tool, published, "-unversioned")
        contains += ["-contains", f"{tool}=={published}"]

    say("staging bundles (skopeo, then umoci -- the big one takes a minute)")
    registry("add-image", f"{PULL_FROM}/sc-runtime:{version}",
             "-digest", runtime_digest,
             "-contains", f"siliconcompiler=={version}", "-stage")
    registry("add-image", f"{PULL_FROM}/sc-tools:{version}",
             "-digest", tools_digest,
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

    runtime_digest = push(RUNTIME_IMAGE, "sc-runtime", version)
    tools_digest = push(STACK_IMAGE, "sc-tools", version)

    register(version, tools_digest, runtime_digest, published)

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
