'''
The wheels a remote run uploads: one per distribution no index can supply
(surface *Uploaded wheels*).

A distribution installed editable, from a local path or file, or from git has a
``direct_url.json`` beside it (PEP 610), and no index would give the server the
same thing. So the client builds it a wheel, and the server installs that with
the rest -- copying files, running none of its code:

- **an editable or local-directory install** is built from its source with
  ``pip wheel --no-deps``, which applies the project's own packaging, its data
  files included;
- **any other install** -- from a file, an archive or git -- is repacked from
  its installed files and ``dist-info`` (:func:`repack`), which is also how a
  package the server asks for by name is answered.

🔴 **Pure only, and refused here otherwise**: a wheel holding a compiled file,
or tagged for a platform, was built for this machine and will not import on the
node. Every wheel is held to the server's own check,
`environment.check_wheel`, before anything is created.
'''

import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from importlib import metadata
from typing import Dict
from urllib.parse import urlsplit
from urllib.request import url2pathname

from siliconcompiler.remote import environment
from siliconcompiler.remote.client.capture import CannotForward, direct_url

__all__ = ["build", "repack"]


# The zip timestamp every member of a repacked wheel carries, so the same
# installed files make the same wheel -- and a server keyed on its digest
# builds the job's packages once.
_EPOCH = (1980, 1, 1, 0, 0, 0)

# What of an installed dist-info is not carried: pip writes these at install,
# and a wheel carries its own RECORD and WHEEL.
_INSTALL_RECORDS = {"RECORD", "INSTALLER", "REQUESTED", "direct_url.json", "WHEEL"}


def build(dist: metadata.Distribution, directory: str) -> str:
    '''A pure wheel of ``dist`` in ``directory``, as its path. Raises
    CannotForward, naming the distribution and why.'''
    name, version = _identity(dist)
    source = _source_directory(direct_url(dist) or {})
    if source is not None:
        path = _pip_wheel(name, version, source, directory)
    else:
        path = repack(dist, directory)
    try:
        environment.check_wheel(path)
    except environment.WheelError as e:
        os.unlink(path)
        # A compiled file is fixed where the platform is known: a wheel built
        # for the server's, on its index. Anything else is the package's own
        # packaging, which the server would reject after the upload.
        fix = ("Publish it to an index, as a wheel for the server's platform"
               if e.compiled else "Change its packaging so its wheel holds no such file")
        raise CannotForward(
            f"{name} {version} is installed here from {source or 'a local source'}, "
            f"and no index can supply it, so it is sent as a wheel; but {e}. {fix}",
            compiled=e.compiled) from None
    return path


def repack(dist: metadata.Distribution, directory: str) -> str:
    '''A wheel of ``dist`` from its installed files and ``dist-info``, as its
    path. Raises CannotForward for one with a compiled file, or with no
    record of what it installed.'''
    name, version = _identity(dist)
    what = f"{name} {version}"
    files = dist.files
    if files is None:
        raise CannotForward(f"{what} records no list of its installed files, so it "
                            "cannot be repacked as a wheel")

    escaped = re.sub(r"[-_.]+", "_", name)
    dist_info = f"{escaped}-{version.replace('-', '_')}.dist-info"
    members: Dict[str, str] = {}
    for entry in files:
        parts = entry.parts
        if not parts or parts[0] == ".." or os.path.isabs(str(entry)):
            # Scripts and data outside site-packages: a console script comes
            # back from entry_points.txt when the wheel is installed.
            continue
        if "__pycache__" in parts or entry.suffix in (".pyc", ".pyo"):
            continue
        if parts[0].endswith(".dist-info"):
            if len(parts) == 2 and parts[1] in _INSTALL_RECORDS:
                continue
            arcname = "/".join((dist_info,) + tuple(parts[1:]))
        else:
            arcname = "/".join(parts)
        if arcname.lower().endswith(environment.COMPILED):
            raise CannotForward(
                f"{what} is installed here from a local source, and no index can supply "
                f"it; it holds a compiled file, {arcname}, built for this machine, which "
                "will not import on the server. Publish it to an index, as a wheel for "
                "the server's platform", compiled=arcname)
        located = str(dist.locate_file(entry))
        if os.path.isfile(located) and not os.path.islink(located):
            members[arcname] = located

    if f"{dist_info}/METADATA" not in members:
        raise CannotForward(f"{what} has no METADATA among its installed files, so it "
                            "cannot be repacked as a wheel")

    wheel = ("Wheel-Version: 1.0\nGenerator: siliconcompiler\n"
             "Root-Is-Purelib: true\nTag: py3-none-any\n").encode()
    path = os.path.join(directory, f"{escaped}-{version.replace('-', '_')}-py3-none-any.whl")
    record = []
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        def add(arcname, data):
            info = zipfile.ZipInfo(arcname, date_time=_EPOCH)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
            record.append(f"{arcname},sha256={digest.decode()},{len(data)}")

        for arcname, located in sorted(members.items()):
            with open(located, "rb") as f:
                add(arcname, f.read())
        add(f"{dist_info}/WHEEL", wheel)
        record.append(f"{dist_info}/RECORD,,")
        info = zipfile.ZipInfo(f"{dist_info}/RECORD", date_time=_EPOCH)
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, "\n".join(record) + "\n")
    return path


def _identity(dist: metadata.Distribution):
    from packaging.version import InvalidVersion, Version

    name = environment.canonical(dist.metadata["Name"] or "")
    try:
        version = str(Version(dist.version))
    except InvalidVersion:
        raise CannotForward(f"{name} is installed here at {dist.version}, which is not "
                            "a PEP 440 version, so it cannot be sent as a wheel") from None
    return name, version


def _source_directory(info: dict):
    '''The local directory an editable or local-directory install came from,
    where it is still there; None for anything else.'''
    url = info.get("url") or ""
    if "dir_info" not in info or not url.startswith("file:"):
        return None
    path = url2pathname(urlsplit(url).path)
    return path if os.path.isdir(path) else None


def _pip_wheel(name: str, version: str, source: str, directory: str) -> str:
    '''``pip wheel --no-deps`` of ``source`` into ``directory``.'''
    out = tempfile.mkdtemp(prefix=".sc-wheel-", dir=directory)
    try:
        # A fixed timestamp where the build backend honours it, so the same
        # source makes the same wheel: 1980-01-02 UTC, which is on or after
        # the first day a zip can record in every timezone.
        env = dict(os.environ, SOURCE_DATE_EPOCH="315619200")
        done = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-input",
             "--disable-pip-version-check", "--wheel-dir", out, source],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env)
        if done.returncode != 0:
            tail = "\n".join(done.stdout.strip().splitlines()[-15:])
            raise CannotForward(
                f"{name} {version} is installed here from {source}, and no index can "
                f"supply it, so it is sent as a wheel; but pip wheel --no-deps {source} "
                f"failed:\n{tail}")
        built = sorted(entry for entry in os.listdir(out) if entry.endswith(".whl"))
        if len(built) != 1:
            raise CannotForward(f"pip wheel --no-deps {source} made {len(built)} wheels "
                                f"for {name}, and one was expected")
        path = os.path.join(directory, built[0])
        shutil.move(os.path.join(out, built[0]), path)
        return path
    finally:
        shutil.rmtree(out, ignore_errors=True)
