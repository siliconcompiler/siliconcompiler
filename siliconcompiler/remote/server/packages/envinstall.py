'''
Installing a job's Python packages on the host, while the job is staging.

Where nodes run on this host -- this server without containers, dispatching
locally -- the job's `python_packages` and its uploaded wheels are installed
here while the job is `staging`, into a cache kept per user, so a package that
will not install rejects the job before any node runs rather than failing the
run. A deployment that runs containers builds a derived image instead --
`envbuild` -- with the same install, `pipbuild`.

🔴 **Nothing the job wrote is handed to pip.** The lists were held to their
grammar at create, and the files pip reads are this server's own, written from
what parsed. **Wheels only**: a source distribution builds only in the isolated
builder. **From the deployment's `package_indexes`**, never an index a job
names. What this Python already holds is never installed a second time -- see
`pipbuild`. The result goes on the tool's `PYTHONPATH` through a `site` link in
the job's directory, and never on SiliconCompiler's own.
'''

import hashlib
import json
import os
import shutil
import sys
import sysconfig
import uuid

from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

from siliconcompiler.remote import environment

__all__ = ["InstallFailed", "HEADER", "install", "recorded", "digest"]


HEADER = ("Written by sc-server from the job's python_packages; nothing the job "
          "wrote is handed to pip.")


class InstallFailed(RuntimeError):
    '''A job's packages that did not install. ``result`` is pipbuild's record.'''

    def __init__(self, result: Dict[str, Any]):
        self.result = result
        super().__init__(
            f"the job's Python packages would not install for {result.get('python')} "
            f"on {result.get('platform')}:\n{result.get('tail', '')}")


def digest(path) -> str:
    '''A wheel's sha256, which is what an install of it is keyed on.'''
    found = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            found.update(chunk)
    return found.hexdigest()


def recorded(target) -> Dict[str, Any]:
    '''What the install of ``target`` added: each distribution with its
    version, each version substituted within its release line, and each listed
    version this host's own copy was kept over -- kept beside the environment,
    so a cached one reports the same as a fresh one (profile §5,
    *`resolved_versions` covers images only*).'''
    try:
        with open(f"{target}.json") as f:
            found = json.load(f)
    except (OSError, ValueError):
        return {"installed": [], "substituted": {}, "ignored": {}}
    return {"installed": [list(pair) for pair in found.get("installed") or []],
            "substituted": dict(found.get("substituted") or {}),
            "ignored": dict(found.get("ignored") or {})}


def install(packages: environment.Packages, wheels: Sequence[str], root: Path, logger,
            constrain=(), indexes=()) -> Tuple[str, Dict[str, Any]]:
    '''A job's packages into a directory of their own, built once and shared
    by every job of this user asking for the same set. Returns the directory
    and what its install added (:func:`recorded`). Raises InstallFailed.

    Keyed by this Python, this platform, what it holds, the indexes, the job's
    `requires.python` names, the files this server writes and each wheel's
    digest -- the install adds to what this Python holds and comes from where
    the indexes say, so all of it is part of what the result means. Built
    under a lock beside it and moved into place whole, so a directory that
    exists is one that is finished.
    '''
    from fasteners import InterProcessLock

    from siliconcompiler.remote.server.packages import pipbuild

    requirements = environment.render(packages.requirements, header=HEADER)
    constraints = environment.render(packages.constraints, header=HEADER)
    wheels = sorted(str(path) for path in wheels)
    tag = sys.implementation.cache_tag
    key = hashlib.sha256(json.dumps({
        "python": tag, "platform": sysconfig.get_platform(),
        "holds": pipbuild.pins(), "indexes": list(indexes),
        "constrain": sorted(environment.canonical(name) for name in constrain),
        "requirements": requirements, "constraints": constraints,
        "wheels": [digest(path) for path in wheels],
    }).encode()).hexdigest()[:16]
    target = Path(root) / f"{tag}-{key}"
    if target.is_dir():
        return str(target), recorded(target)

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with InterProcessLock(f"{target}.lock"):
        if target.is_dir():
            return str(target), recorded(target)

        staging = Path(f"{target}.{uuid.uuid4().hex}")
        listed = Path(f"{staging}.requirements.txt")
        limited = Path(f"{staging}.constraints.txt")
        listed.write_text(requirements)
        limited.write_text(constraints)
        named = [str(pin) for pin in packages.requirements] + \
            [os.path.basename(path) for path in wheels]
        logger.info(f"Installing the job's Python packages into {target}: "
                    f"{', '.join(named) or 'nothing beyond what this host holds'}")
        try:
            result = pipbuild.install(str(listed), str(limited), str(staging),
                                      wheels=wheels, indexes=indexes)
        finally:
            listed.unlink(missing_ok=True)
            limited.unlink(missing_ok=True)
        if result["returncode"] != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallFailed(result)
        # Nothing to install is still an environment: this host held it all.
        staging.mkdir(exist_ok=True)
        with open(f"{target}.json", "w") as f:
            json.dump({"installed": [list(pair) for pair in result.get("installed") or []],
                       "substituted": {name: list(pair) for name, pair in
                                       (result.get("substituted") or {}).items()},
                       "ignored": {name: list(pair) for name, pair in
                                   (result.get("ignored") or {}).items()}}, f)
        os.rename(staging, target)

    return str(target), recorded(target)
