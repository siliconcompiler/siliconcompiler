'''
A job's Python packages: the create body's `python_packages` (``requirements``
and ``constraints``) and the wheels it uploads (surface *A node's own Python
packages, built while staging*).

One grammar at both ends: each entry exactly ``name==version``, canonical,
each name once, within :data:`MAX_ENTRIES` and :data:`MAX_BYTES`. No entry
names an index, and the lists never reach pip: the server writes its own files
from what :func:`parse` accepted (:func:`render`).

A wheel is pure or refused (:func:`check_wheel`).
'''

import email.parser
import json
import os
import re
import stat
import zipfile

from typing import Any, Iterable, NamedTuple, Optional, Sequence, Tuple

from packaging.utils import InvalidWheelFilename, parse_wheel_filename
# A distribution name as PEP 503 compares it.
from packaging.utils import canonicalize_name as canonical
from packaging.version import InvalidVersion, Version

__all__ = ["MAX_BYTES", "MAX_ENTRIES", "WHEELS", "COMPILED", "ROOT", "SITE", "IMAGE_SITE",
           "PackagesError", "WheelError", "Pin", "Packages", "Wheel", "canonical",
           "parse_entry", "parse", "render", "wheels_path", "site_path", "wheel_name",
           "check_wheel"]


MAX_BYTES = 64 * 1024
MAX_ENTRIES = 1000

# The wheels' folder under the collection directory: unhashed, so it collides
# with no other collected folder.
WHEELS = "python"

# Compiled extensions, built for the submitting machine.
COMPILED = (".so", ".pyd", ".dylib")

# Host mode's install for the job, relative to the job directory: a link the
# server writes after extraction, which an upload may not carry.
ROOT = "sc_python"
SITE = "site"

# A derived image's install, its own layer, reaching only the tool's PYTHONPATH.
IMAGE_SITE = "/opt/sc/python-env/site"

_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_ENTRY = re.compile(rf"^(?P<name>{_NAME})==(?P<version>\S+)$")

# The bound on each metadata file read from a wheel.
_METADATA_LIMIT = 1024 * 1024


class PackagesError(ValueError):
    '''`python_packages` outside its grammar or bounds; ``entry`` names the entry.'''

    def __init__(self, why: str, entry: Optional[str] = None):
        super().__init__(f"{entry!r}: {why}" if entry is not None else why)
        self.why, self.entry = why, entry


class WheelError(ValueError):
    '''Not a pure, well-formed wheel; ``compiled`` names a compiled file that is why.'''

    def __init__(self, message: str, compiled: Optional[str] = None):
        super().__init__(message)
        self.compiled = compiled


class Pin(NamedTuple):
    name: str
    version: str

    def __str__(self) -> str:
        return f"{self.name}=={self.version}"


class Packages(NamedTuple):
    requirements: Tuple[Pin, ...] = ()
    constraints: Tuple[Pin, ...] = ()

    def names(self):
        '''Every name listed, canonical.'''
        return {canonical(pin.name) for pin in self.requirements + self.constraints}

    def without(self, names: Iterable[str]) -> "Packages":
        '''The lists less ``names``, which wheels replace.'''
        drop = {canonical(name) for name in names}
        return Packages(tuple(pin for pin in self.requirements if canonical(pin.name) not in drop),
                        tuple(pin for pin in self.constraints if canonical(pin.name) not in drop))

    def wire(self) -> dict:
        return {"requirements": [str(pin) for pin in self.requirements],
                "constraints": [str(pin) for pin in self.constraints]}


class Wheel(NamedTuple):
    name: str                   # canonical
    version: str
    filename: str
    members: int = 0            # what it holds, held to the extraction limits
    expanded: int = 0           # its members' bytes, uncompressed


def parse_entry(text: Any) -> Pin:
    '''One entry, held to the grammar. Raises PackagesError naming it.'''
    if not isinstance(text, str):
        raise PackagesError("an entry is a string", json.dumps(text)[:80])
    found = _ENTRY.match(text)
    if not found:
        raise PackagesError(
            "not exactly name==version: extras, a marker, a range, a URL, a path, "
            "an option and whitespace are all refused", text)
    try:
        canonical_form = str(Version(found["version"])) == found["version"]
    except InvalidVersion:
        canonical_form = False
    if not canonical_form:
        raise PackagesError(f"{found['version']} is not a PEP 440 version in its "
                            "canonical form", text)
    return Pin(found["name"], found["version"])


def parse(member: Any) -> Packages:
    '''`python_packages`, held to its grammar and bounds. Raises PackagesError.'''
    if not isinstance(member, dict):
        raise PackagesError("python_packages is an object of requirements and "
                            "constraints")
    unknown = sorted(set(member) - {"requirements", "constraints"})
    if unknown:
        raise PackagesError(f"python_packages has no member {unknown[0]!r}; it takes "
                            "requirements and constraints")
    lists = {}
    for field in ("requirements", "constraints"):
        entries = member.get(field)
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise PackagesError(f"python_packages.{field} is a list of name==version")
        lists[field] = entries

    total = len(lists["requirements"]) + len(lists["constraints"])
    if total > MAX_ENTRIES:
        raise PackagesError(f"python_packages lists {total} entries, and at most "
                            f"{MAX_ENTRIES} are taken")
    size = len(json.dumps(member, separators=(",", ":")).encode())
    if size > MAX_BYTES:
        raise PackagesError(f"python_packages is {size} bytes, and at most {MAX_BYTES} "
                            "are taken")

    seen = set()
    parsed = {}
    for field in ("requirements", "constraints"):
        pins = []
        for entry in lists[field]:
            pin = parse_entry(entry)
            key = canonical(pin.name)
            if key in seen:
                raise PackagesError(f"{pin.name} is named twice across both lists", entry)
            seen.add(key)
            pins.append(pin)
        parsed[field] = tuple(pins)
    return Packages(parsed["requirements"], parsed["constraints"])


def render(pins: Sequence[Pin], header: str = "") -> str:
    '''A requirements or constraints file written from parsed pins, never the job's text.'''
    lines = [f"# {line}" if line else "#" for line in header.splitlines()]
    lines.extend(f"{canonical(pin.name)}=={pin.version}" for pin in pins)
    return "\n".join(lines) + "\n"


def wheels_path() -> str:
    '''Where the uploaded wheels sit, relative to the archive root.'''
    return f"sc_collected_files/{WHEELS}"


def site_path() -> str:
    '''Where host mode links what it installed, relative to the job.'''
    return f"{ROOT}/{SITE}"


def wheel_name(filename: str) -> Optional[str]:
    '''The canonical distribution a wheel's file name names (PEP 427), or None.'''
    try:
        return parse_wheel_filename(os.path.basename(filename))[0]
    except (InvalidWheelFilename, InvalidVersion):
        return None


def check_wheel(path) -> Wheel:
    '''The wheel at ``path``, held to what an upload may carry: ``none-any``,
    members confined, no link, device or compiled file, one matching
    ``.dist-info``. Reads only; runs nothing.

    Nothing that runs by itself and no dependency by URL (surface D292): a
    ``.pth``, ``sitecustomize.py``, ``usercustomize.py``, a ``.data/`` directory
    or a ``name @ url`` requirement would let installing run or fetch code.
    '''
    filename = os.path.basename(str(path))
    try:
        name, version, _, tags = parse_wheel_filename(filename)
    except (InvalidWheelFilename, InvalidVersion):
        raise WheelError(f"{filename} is not named as a wheel is, "
                         "<name>-<version>-<python>-<abi>-<platform>.whl, with a "
                         "PEP 440 version") from None
    if any(tag.abi != "none" or tag.platform != "any" for tag in tags):
        tagged = "-".join(".".join(sorted({getattr(tag, part) for tag in tags}))
                          for part in ("abi", "platform"))
        raise WheelError(f"{filename} is tagged {tagged}, and "
                         "only a pure wheel, none-any, is taken")

    try:
        archive = zipfile.ZipFile(str(path))
    except (zipfile.BadZipFile, OSError) as e:
        raise WheelError(f"{filename} is not a zip file: {e}") from None
    with archive:
        infos = archive.infolist()
        metadata_dirs = set()
        for info in infos:
            member = info.filename
            parts = member.rstrip("/").split("/")
            if not member or member.startswith("/") or "\\" in member or \
                    any(part in ("", ".", "..") for part in parts):
                raise WheelError(f"{filename} holds {member!r}, which does not stay "
                                 "inside it")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise WheelError(f"{filename} holds a link, {member}")
            if stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) \
                    or stat.S_ISSOCK(mode):
                raise WheelError(f"{filename} holds a device, {member}")
            if member.lower().endswith(".pth"):
                raise WheelError(f"{filename} holds {member}, a .pth file, which runs "
                                 "in any Python that starts with it on its path")
            if len(parts) == 1 and parts[0] in _RUNS_AT_START:
                raise WheelError(f"{filename} holds {member}, which runs in any Python "
                                 "that starts with it on its path")
            if parts[0].endswith(".data"):
                raise WheelError(f"{filename} holds {parts[0]}/, which installs outside "
                                 "the package")
            if member.lower().endswith(COMPILED):
                raise WheelError(f"{filename} holds a compiled file, {member}, which "
                                 "will not import on another machine", compiled=member)
            if parts[0].endswith(".dist-info"):
                metadata_dirs.add(parts[0])

        if len(metadata_dirs) != 1:
            raise WheelError(f"{filename} holds {len(metadata_dirs)} .dist-info "
                             "directories, and a wheel holds one")
        dist_info, = metadata_dirs
        inner_name, _, inner_version = dist_info[:-len(".dist-info")].rpartition("-")
        try:
            same = canonical(inner_name) == name and Version(inner_version) == version
        except InvalidVersion:
            same = False
        if not same:
            raise WheelError(f"{filename} holds {dist_info}, which names another "
                             "distribution or version")

        def read(member):
            try:
                info = archive.getinfo(f"{dist_info}/{member}")
            except KeyError:
                raise WheelError(f"{filename} has no {dist_info}/{member}") from None
            if info.file_size > _METADATA_LIMIT:
                raise WheelError(f"{filename}'s {member} is larger than "
                                 f"{_METADATA_LIMIT} bytes")
            try:
                return archive.read(info).decode("utf-8")
            except (UnicodeDecodeError, zipfile.BadZipFile, OSError) as e:
                raise WheelError(f"{filename}'s {member} cannot be read: {e}") from None

        metadata = email.parser.Parser().parsestr(read("METADATA"), headersonly=True)
        try:
            same = canonical(metadata.get("Name") or "") == name and \
                Version(metadata.get("Version") or "") == version
        except InvalidVersion:
            same = False
        if not same:
            raise WheelError(f"{filename}'s METADATA names another distribution or "
                             "version")
        for requirement in metadata.get_all("Requires-Dist") or []:
            if _direct_reference(requirement):
                raise WheelError(f"{filename} depends on {requirement.strip()}, a "
                                 "dependency by URL, which the install would fetch from "
                                 "wherever it points")

        wheel = email.parser.Parser().parsestr(read("WHEEL"), headersonly=True)
        if (wheel.get("Root-Is-Purelib") or "").strip().lower() != "true":
            raise WheelError(f"{filename} does not install as pure Python "
                             "(Root-Is-Purelib is not true)")
        tags = wheel.get_all("Tag") or []
        if not tags or any(not tag.strip().endswith("-none-any") for tag in tags):
            raise WheelError(f"{filename}'s WHEEL tags it for a platform: "
                             f"{', '.join(tag.strip() for tag in tags) or 'no tag'}")

    return Wheel(name, str(version), filename, len(infos),
                 sum(info.file_size for info in infos))


# What runs in any Python that merely starts with a wheel on its path.
_RUNS_AT_START = ("sitecustomize.py", "usercustomize.py")


def _direct_reference(requirement: str) -> bool:
    '''Whether a `Requires-Dist` entry is ``name @ url``; an unparsable one counts.'''
    from packaging.requirements import InvalidRequirement, Requirement

    try:
        return Requirement(requirement).url is not None
    except InvalidRequirement:
        return True
