'''
A job's Python packages: the create body's `python_packages`, and the wheels
the job uploads (surface *A node's own Python packages, built while staging*).

A testbench imports whatever its author had installed -- cocotb's plugins, a UVM
library, `numpy` -- and the submitting machine is the one place that environment
is known to exist. So the client lists it, once per job, in two lists of
``name==version``: ``requirements``, the distributions the run's Python code
imports, and ``constraints``, the version of every other distribution installed
there. A distribution no index can supply -- installed editable, from a local
path or file, or from git -- travels instead as a wheel the client built, under
``sc_collected_files/python/``. The user's own modules are neither: they are
collected files, in their test's collected folder.

🔴 **The lists are held to one grammar at both ends.** Every entry is exactly
``name==version``: a PEP 508 name and a PEP 440 version in its canonical form,
with no extras, marker, range, URL, path or option. Each name once across both
lists; together at most :data:`MAX_ENTRIES` entries and :data:`MAX_BYTES`. **No
entry names an index**: every package comes from the deployment's own. **The
lists are never handed to pip**: the server writes its own requirements and
constraints files from what :func:`parse` accepted, with :func:`render`.

🔴 **A wheel is pure or it is refused** (:func:`check_wheel`): tagged
``none-any``, holding no compiled file, and saying inside what its name says
outside. Installing a wheel copies files and runs none of its code.
'''

import email.parser
import json
import os
import re
import stat
import zipfile

from typing import Any, Iterable, NamedTuple, Optional, Sequence, Tuple

__all__ = ["MAX_BYTES", "MAX_ENTRIES", "WHEELS", "COMPILED", "ROOT", "SITE", "IMAGE_SITE",
           "PackagesError", "WheelError", "Pin", "Packages", "Wheel", "canonical",
           "parse_entry", "parse", "render", "wheels_path", "site_path", "wheel_name",
           "check_wheel"]


MAX_BYTES = 64 * 1024
MAX_ENTRIES = 1000

# Where the uploaded wheels sit, under the collection directory. No hash
# suffix, and every other collected folder has one, so it collides with none.
WHEELS = "python"

# A compiled extension: built for the submitting machine, so it will not import
# on the node.
COMPILED = (".so", ".pyd", ".dylib")

# Where host mode puts what it installed for the job, relative to the job's
# directory: a link into the user's cache that the server writes after the
# upload is extracted, and an upload may not carry.
ROOT = "sc_python"
SITE = "site"

# Where a derived image puts what was installed for the job -- the container
# mode's `site`. Absolute, inside the image; its own layer, never the image's
# own site-packages, so it reaches the tool's PYTHONPATH and nothing else.
IMAGE_SITE = "/opt/sc/python-env/site"

# A PEP 508 name, which is what normalises under PEP 503.
_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_ENTRY = re.compile(rf"^(?P<name>{_NAME})==(?P<version>\S+)$")

# A PEP 440 version in its canonical form: what `packaging` prints it as.
_VERSION = re.compile(
    r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*"
    r"((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?"
    r"(\+[a-z0-9]+(\.[a-z0-9]+)*)?$")

# A wheel's name (PEP 427): distribution, version, optional build tag, then the
# python, abi and platform tags.
_WHEEL = re.compile(r"^(?P<name>[A-Za-z0-9_.]+)-(?P<version>[A-Za-z0-9_.!+]+)"
                    r"(-(?P<build>\d[A-Za-z0-9_.]*))?-(?P<python>[A-Za-z0-9_.]+)"
                    r"-(?P<abi>[A-Za-z0-9_.]+)-(?P<platform>[A-Za-z0-9_.]+)\.whl$")

# What of a wheel is read to check it: its two metadata files, each bounded.
_METADATA_LIMIT = 1024 * 1024


class PackagesError(ValueError):
    '''`python_packages` outside its grammar or its bounds. ``entry`` is the
    entry named, where there is one.'''

    def __init__(self, why: str, entry: Optional[str] = None):
        super().__init__(f"{entry!r}: {why}" if entry is not None else why)
        self.why, self.entry = why, entry


class WheelError(ValueError):
    '''A file that is not a pure, well-formed wheel.'''


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
        '''The lists less ``names``: what a wheel of the same distribution
        replaces.'''
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


def canonical(name: str) -> str:
    '''A distribution name as PEP 503 compares it.'''
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_entry(text: Any) -> Pin:
    '''One entry, held to the grammar. Raises PackagesError naming it.'''
    if not isinstance(text, str):
        raise PackagesError("an entry is a string", json.dumps(text)[:80])
    found = _ENTRY.match(text)
    if not found:
        raise PackagesError(
            "not exactly name==version: extras, a marker, a range, a URL, a path, "
            "an option and whitespace are all refused", text)
    if not _VERSION.match(found["version"]):
        raise PackagesError(f"{found['version']} is not a PEP 440 version in its "
                            "canonical form", text)
    return Pin(found["name"], found["version"])


def parse(member: Any) -> Packages:
    '''`python_packages`, held to its grammar and bounds. Raises
    PackagesError.'''
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
    '''A requirements or constraints file of the builder's own, written from
    what :func:`parse` accepted -- never the job's text handed on.'''
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
    '''The canonical distribution a wheel's file name says it is, or None for
    a name that is not a wheel's.'''
    found = _WHEEL.match(os.path.basename(filename))
    return canonical(found["name"]) if found else None


def check_wheel(path) -> Wheel:
    '''The wheel at ``path``, held to what an upload may carry: named as a
    wheel is, tagged ``none-any``, a zip whose members stay inside it and are
    no link and no compiled file, with one ``.dist-info`` that says the same
    name and version as the file name. Raises WheelError.

    Reads the zip's directory and its two metadata files, and runs nothing.
    '''
    from packaging.version import InvalidVersion, Version

    filename = os.path.basename(str(path))
    found = _WHEEL.match(filename)
    if not found:
        raise WheelError(f"{filename} is not named as a wheel is, "
                         "<name>-<version>-<python>-<abi>-<platform>.whl")
    if set(found["abi"].split(".")) != {"none"} or \
            set(found["platform"].split(".")) != {"any"}:
        raise WheelError(f"{filename} is tagged {found['abi']}-{found['platform']}, and "
                         "only a pure wheel, none-any, is taken")
    name = canonical(found["name"])
    try:
        version = Version(found["version"].replace("_", "-"))
    except InvalidVersion:
        raise WheelError(f"{filename} does not carry a PEP 440 version") from None

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
            if stat.S_ISLNK(info.external_attr >> 16):
                raise WheelError(f"{filename} holds a link, {member}")
            if member.lower().endswith(COMPILED):
                raise WheelError(f"{filename} holds a compiled file, {member}, which "
                                 "will not import on another machine")
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

        wheel = email.parser.Parser().parsestr(read("WHEEL"), headersonly=True)
        if (wheel.get("Root-Is-Purelib") or "").strip().lower() != "true":
            raise WheelError(f"{filename} does not install as pure Python "
                             "(Root-Is-Purelib is not true)")
        tags = wheel.get_all("Tag") or []
        if not tags or any(not tag.strip().endswith("-none-any") for tag in tags):
            raise WheelError(f"{filename}'s WHEEL tags it for a platform: "
                             f"{', '.join(tag.strip() for tag in tags) or 'no tag'}")

    return Wheel(name, str(version), filename)
