'''
A node's own Python packages, as a file the client writes and the server parses.

A testbench imports whatever its author had installed -- cocotb's plugins, a UVM
library, `numpy` -- and the submitting machine is the one place that environment
is known to exist. So the client writes it down, one file per node that needs
one, at ``python-env/<step>/<index>/requirements.txt`` in the first archive; the
file's presence is the declaration (surface D131).

🔴 **The format is closed, and both ends hold it to the same grammar.** Every
line is blank, a comment, ``--index-url <URL>`` (at most one),
``--extra-index-url <URL>``, or ``name[extras]==version`` with an optional
``; <marker>`` -- a PEP 503 name, exactly one ``==`` and a full PEP 440 version,
each name once. Everything else is refused: every other option, a URL or VCS
requirement, a local path, a continuation. **The file is never handed to pip**:
a builder writes its own from what :func:`parse` accepted, so a line pip would
read one way and this grammar another has no route through.
'''

import re

from typing import List, NamedTuple, Optional, Sequence
from urllib.parse import urlsplit

__all__ = ["ROOT", "FILENAME", "PACKAGES", "MAX_BYTES", "MAX_LINES",
           "SITE", "EnvironmentFileError", "Pin", "Environment", "path_for",
           "packages_path", "site_path", "parse", "render"]


ROOT = "python-env"
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
    index_url: Optional[str]
    extra_index_urls: List[str]

    @property
    def indexes(self) -> List[str]:
        '''Every index the file names, the replacing one first.'''
        return ([self.index_url] if self.index_url else []) + list(self.extra_index_urls)


# Where a node's forwarded packages -- editable, local and VCS installs, which
# no index reproduces -- sit beside its file. The user's own code: uploaded, put
# on the tool's PYTHONPATH, never installed.
PACKAGES = "packages"


def path_for(step: str, index: str) -> str:
    '''Where a node's file sits, relative to the archive root.'''
    return f"{ROOT}/{step}/{index}/{FILENAME}"


def packages_path(step: str, index: str) -> str:
    '''Where a node's forwarded packages sit, relative to the archive root.'''
    return f"{ROOT}/{step}/{index}/{PACKAGES}"


# Beside a node's file, on the node: what the server installed from it.
SITE = "site"


def site_path(step: str, index: str) -> str:
    '''Where what was installed for a node is reached, relative to the job.'''
    return f"{ROOT}/{step}/{index}/{SITE}"


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
    index_url = None
    extras: List[str] = []

    for number, raw in enumerate(lines, start=1):
        line = raw[:-1] if raw.endswith("\r") else raw
        if line.rstrip().endswith("\\"):
            raise EnvironmentFileError("a line continuation", number)
        line = _COMMENT.sub("", line).strip()
        if not line:
            continue

        if line.startswith("-"):
            option, _, url = line.partition(" ")
            url = url.strip()
            if option not in ("--index-url", "--extra-index-url") or not url or " " in url:
                raise EnvironmentFileError(f"{option} is not an option this format takes",
                                           number)
            _check_url(url, number)
            if option == "--index-url":
                if index_url is not None:
                    raise EnvironmentFileError("a second --index-url", number)
                index_url = url
            else:
                extras.append(url)
            continue

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

    return Environment(pins, index_url, extras)


def _check_url(url: str, number: int) -> None:
    try:
        parts = urlsplit(url)
    except ValueError:
        raise EnvironmentFileError("an index that is not a URL", number) from None
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise EnvironmentFileError("an index that is not an http or https URL", number)
    if parts.username is not None or parts.password is not None:
        # 🔴 An index's credential comes from the operator, keyed by its
        # allowlist entry -- never from the user's file.
        raise EnvironmentFileError("an index URL carrying credentials", number)


def render(pins: Sequence[Pin], index_url: Optional[str] = None,
           extra_index_urls: Sequence[str] = (), header: str = "") -> str:
    '''A file in the format -- what a client writes, and what a builder writes
    from what it parsed rather than handing the user's file on.'''
    lines = [f"# {line}" if line else "#" for line in header.splitlines()]
    if index_url:
        lines.append(f"--index-url {index_url}")
    lines.extend(f"--extra-index-url {url}" for url in extra_index_urls)
    lines.extend(str(pin) for pin in pins)
    return "\n".join(lines) + "\n"
