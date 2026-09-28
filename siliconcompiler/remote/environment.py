'''
A node's own Python packages, as a file the client writes and the server parses.

A testbench imports whatever its author had installed -- cocotb's plugins, a UVM
library, `numpy` -- and the submitting machine is the one place that environment
is known to exist. So the client writes it down, one file per executed node with
a package to install, at ``sc_python/nodes/<step>/<index>/requirements.txt`` in
the first archive; the file's presence is the declaration. The user's own code
travels once per job beside it, in ``sc_python/packages/`` (surface *A node's
own Python packages, built while staging*).

🔴 **The format is closed, and both ends hold it to the same grammar.** Every
line is blank, a comment, or ``name[extras]==version`` with an optional
``; <marker>`` -- a PEP 503 name, exactly one ``==`` and a full PEP 440 version,
each name once. Everything else is refused: every option line, an index among
them, a URL or VCS requirement, a local path, a continuation. **No line names an
index**: every package comes from the deployment's own. **The file is never
handed to pip**: a builder writes its own from what :func:`parse` accepted, so a
line pip would read one way and this grammar another has no route through.
'''

import re

from typing import List, NamedTuple, Optional, Sequence

__all__ = ["ROOT", "NODES", "FILENAME", "PACKAGES", "MAX_BYTES", "MAX_LINES",
           "SITE", "IMAGE_SITE", "EnvironmentFileError", "Pin", "Environment", "path_for",
           "packages_path", "site_path", "parse", "render"]


ROOT = "sc_python"
NODES = "nodes"
FILENAME = "requirements.txt"
MAX_BYTES = 64 * 1024
MAX_LINES = 1000

# A PEP 508 name, which is what normalises under PEP 503.
_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_REQUIREMENT = re.compile(
    rf"^(?P<name>{_NAME})(?:\[(?P<extras>[^\]]*)\])?\s*==\s*(?P<version>[^\s;]+)"
    r"\s*(?:;\s*(?P<marker>.*\S))?\s*$")
# A comment is `#` on its own or after whitespace, so `a==1#b` is not one.
_COMMENT = re.compile(r"(^|\s)#.*$")


class EnvironmentFileError(ValueError):
    '''A file outside the format. ``line`` is 1-based, or None for the file.'''

    def __init__(self, why: str, line: Optional[int] = None):
        super().__init__(f"line {line}: {why}" if line else why)
        self.why, self.line = why, line


class Pin(NamedTuple):
    name: str
    extras: tuple
    version: str
    marker: Optional[str]

    def __str__(self) -> str:
        extras = f"[{','.join(self.extras)}]" if self.extras else ""
        marker = f" ; {self.marker}" if self.marker else ""
        return f"{self.name}{extras}=={self.version}{marker}"


class Environment(NamedTuple):
    pins: List[Pin]


# Where the user's own code sits, once per job beside the files: the helper
# modules the tests import, and editable, local and VCS installs, which no index
# reproduces. It comes from one Python installation, so every node gets the same
# copy. Laid out as a site-packages directory -- each top-level entry a module
# or package under its import name -- and put first on the tool's PYTHONPATH of
# every node whose task runs the user's Python. Uploaded, never installed.
PACKAGES = "packages"


def path_for(step: str, index: str) -> str:
    '''Where a node's file sits, relative to the archive root.'''
    return f"{ROOT}/{NODES}/{step}/{index}/{FILENAME}"


def packages_path() -> str:
    '''Where the job's uploaded packages sit, relative to the archive root.'''
    return f"{ROOT}/{PACKAGES}"


# Beside a node's file, on the node: what the server installed from it. The
# server writes it after extraction, and an upload carrying one is refused.
SITE = "site"


def site_path(step: str, index: str) -> str:
    '''Where what was installed for a node is reached, relative to the job.'''
    return f"{ROOT}/{NODES}/{step}/{index}/{SITE}"


# Where a derived image puts what was installed for a node -- the container
# mode's `site`. Absolute, inside the image; its own layer, never the image's
# own site-packages, so it reaches the tool's PYTHONPATH and nothing else.
IMAGE_SITE = "/opt/sc/python-env/site"


def parse(data: bytes) -> Environment:
    '''The file, held to the format. Raises EnvironmentFileError.'''
    from packaging.markers import InvalidMarker, Marker
    from packaging.utils import canonicalize_name
    from packaging.version import InvalidVersion, Version

    if len(data) > MAX_BYTES:
        raise EnvironmentFileError(f"it is more than {MAX_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise EnvironmentFileError("it is not UTF-8") from None
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    if len(lines) > MAX_LINES:
        raise EnvironmentFileError(f"it is more than {MAX_LINES} lines")

    pins: List[Pin] = []
    seen = set()

    for number, raw in enumerate(lines, start=1):
        line = raw[:-1] if raw.endswith("\r") else raw
        if line.rstrip().endswith("\\"):
            raise EnvironmentFileError("a line continuation", number)
        line = _COMMENT.sub("", line).strip()
        if not line:
            continue

        if line.startswith("-"):
            # 🔴 Every option, an index among them: every package comes from
            # the deployment's own indexes, and an index credential is never
            # the job's.
            raise EnvironmentFileError(f"{line.split()[0]} is an option, and this "
                                       "format takes none", number)

        found = _REQUIREMENT.match(line)
        if not found:
            raise EnvironmentFileError(
                "not name[extras]==version: a range, a URL, a VCS or local path, "
                "and every other form are refused", number)

        version = found["version"]
        if "*" in version or version.startswith("="):
            raise EnvironmentFileError(f"{version} is not a full version", number)
        try:
            Version(version)
        except InvalidVersion:
            raise EnvironmentFileError(f"{version} is not a PEP 440 version", number) from None

        names = tuple(part.strip() for part in (found["extras"] or "").split(",")
                      if part.strip())
        if any(not re.fullmatch(_NAME, extra) for extra in names):
            raise EnvironmentFileError("an extra that is not a name", number)

        marker = found["marker"]
        if marker is not None:
            try:
                Marker(marker)
            except InvalidMarker:
                raise EnvironmentFileError("a marker that is not PEP 508", number) from None

        key = canonicalize_name(found["name"])
        if key in seen:
            raise EnvironmentFileError(f"{found['name']} is named twice", number)
        seen.add(key)
        pins.append(Pin(found["name"], names, version, marker))

    return Environment(pins)


def render(pins: Sequence[Pin], header: str = "") -> str:
    '''A file in the format -- what a client writes, and what a builder writes
    from what it parsed rather than handing the user's file on.'''
    lines = [f"# {line}" if line else "#" for line in header.splitlines()]
    lines.extend(str(pin) for pin in pins)
    return "\n".join(lines) + "\n"
