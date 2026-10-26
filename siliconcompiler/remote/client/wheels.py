'''
The wheels a remote run uploads, one per distribution no index can supply
(PEP 610 ``direct_url.json``): a local-directory
install is built with ``pip wheel --no-deps``, anything else repacked from its
installed files (:func:`repack`).

Pure only: a compiled or platform-tagged wheel will not import on the node,
so each is held to the server's own `environment.check_wheel` before create.
'''

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from importlib import metadata
from typing import Callable, Dict, List, Optional
from urllib.parse import urlsplit
from urllib.request import url2pathname

from siliconcompiler.remote import environment
from siliconcompiler.remote.client.capture import CannotForward, direct_url

__all__ = ["build", "repack"]


# Fixed, so the same files make the same wheel and digest, which the server caches by.
_EPOCH = (1980, 1, 1, 0, 0, 0)

# Written by pip at install; a wheel carries its own RECORD and WHEEL.
_INSTALL_RECORDS = {"RECORD", "INSTALLER", "REQUESTED", "direct_url.json", "WHEEL"}


def build(dist: metadata.Distribution, directory: str,
          warn: Optional[Callable[[str], None]] = None) -> str:
    '''Build a pure wheel of ``dist`` in ``directory``; returns its path.
    ``warn`` hears of files an editable install has that its wheel leaves out.'''
    name, version = _identity(dist)
    info = direct_url(dist) or {}
    source = _source_directory(info)
    if source is not None:
        path = _pip_wheel(name, version, source, directory)
    else:
        path = repack(dist, directory)
    try:
        environment.check_wheel(path)
    except environment.WheelError as e:
        os.unlink(path)
        fix = ("Publish it to an index, as a wheel for the server's platform"
               if e.compiled else "Change its packaging so its wheel holds no such file")
        raise CannotForward(
            f"{name} {version} is installed here from {source or 'a local source'}, "
            f"and no index can supply it, so it is sent as a wheel; but {e}. {fix}",
            compiled=e.compiled) from None
    if warn is not None and source is not None and (info.get("dir_info") or {}).get("editable"):
        missing = _left_out(path, source)
        if missing:
            warn(f"{name} {version} is installed editable from {source}, and the wheel "
                 f"its packaging builds leaves out {', '.join(missing)}, which its module "
                 "directory holds: the node will not have them. Add them to the "
                 "project's package data")
    return path


def _left_out(wheel: str, source: str) -> List[str]:
    '''Files in ``source``'s module directories (top or ``src/``) the wheel lacks,
    bytecode, dotfiles and links aside.'''
    with zipfile.ZipFile(wheel) as archive:
        held = set(archive.namelist())
    tops = {member.split("/", 1)[0] for member in held if "/" in member}
    tops = {top for top in tops if not top.endswith((".dist-info", ".data"))}

    missing = []
    for top in sorted(tops):
        for base in (source, os.path.join(source, "src")):
            where = os.path.join(base, top)
            if not os.path.isdir(where):
                continue
            for root, dirs, files in os.walk(where):
                dirs[:] = sorted(entry for entry in dirs if entry != "__pycache__"
                                 and not entry.startswith("."))
                for entry in sorted(files):
                    full = os.path.join(root, entry)
                    if entry.startswith(".") or entry.endswith((".pyc", ".pyo")) or \
                            os.path.islink(full):
                        continue
                    if os.path.relpath(full, base).replace(os.sep, "/") not in held:
                        missing.append(os.path.relpath(full, source).replace(os.sep, "/"))
            break
    return missing


def repack(dist: metadata.Distribution, directory: str) -> str:
    '''Repack ``dist`` as a wheel from its installed files; returns its path.'''
    name, version = _identity(dist)
    what = f"{name} {version}"
    files = dist.files
    if files is None:
        raise CannotForward(f"{what} records no list of its installed files, so it "
                            "cannot be repacked as a wheel")

    stem = f"{name.replace('-', '_')}-{version}"
    dist_info = f"{stem}.dist-info"
    members: Dict[str, str] = {}
    for entry in files:
        parts = entry.parts
        if not parts or parts[0] == ".." or os.path.isabs(str(entry)):
            # Outside site-packages: console scripts return from entry_points.txt.
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
    path = os.path.join(directory, f"{stem}-py3-none-any.whl")
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
    '''The local directory an install came from, if still there; else None.'''
    url = info.get("url") or ""
    if "dir_info" not in info or not url.startswith("file:"):
        return None
    path = url2pathname(urlsplit(url).path)
    return path if os.path.isdir(path) else None


def _pip_wheel(name: str, version: str, source: str, directory: str) -> str:
    '''``pip wheel --no-deps`` of ``source`` into ``directory``.'''
    out = tempfile.mkdtemp(prefix=".sc-wheel-", dir=directory)
    try:
        # Reproducible where the backend honours it: 1980-01-02 UTC is a valid
        # zip date in every timezone.
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
