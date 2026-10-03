'''
Installing a job's Python packages on the host, while the job is staging, so
one that will not install rejects the job before any node runs. A deployment
running containers builds a derived image instead (`envbuild`), with the same
install (`pipbuild`).

🔴 Each install is an environment of its own, by key, with its own pip cache
(implementation-notes §L): the second job asking for a key waits and reuses.
🔴 Nothing the job wrote is handed to pip: the files are this server's, wheels
only (source builds only in the isolated builder), from `package_indexes`
only. The result goes on the tool's `PYTHONPATH`, never SiliconCompiler's.
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
    from siliconcompiler.utils import file_digest

    return file_digest(path).hexdigest()


def recorded(target) -> Dict[str, Any]:
    '''What the install of ``target`` added, kept beside it so a cached one reports alike.

    Installed, substituted and ignored versions (profile §5).'''
    try:
        with open(f"{target}.json") as f:
            found = json.load(f)
    except (OSError, ValueError):
        return {"installed": [], "substituted": {}, "ignored": {}, "yanked": []}
    return {"installed": [list(pair) for pair in found.get("installed") or []],
            "substituted": dict(found.get("substituted") or {}),
            "ignored": dict(found.get("ignored") or {}),
            "yanked": list(found.get("yanked") or [])}


def install(packages: environment.Packages, wheels: Sequence[str], root: Path, logger,
            constrain=(), indexes=(), timeout=None, echo=None) -> Tuple[str, Dict[str, Any]]:
    '''Install a job's packages under ``root``, once per set; returns (directory, :func:`recorded`).

    Keyed by everything the result depends on: this Python, platform and
    holdings, the indexes and every input file. Built under a lock and moved
    into place whole, so an existing directory is finished. Raises InstallFailed.
    '''
    from siliconcompiler.remote.server.packages import pipbuild
    from siliconcompiler.utils.multiprocessing import get_file_lock

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
    # Excludes processes and threads alike: two jobs staging are threads.
    with get_file_lock(target).locked():
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
                                      wheels=wheels, indexes=indexes, timeout=timeout,
                                      echo=echo)
        finally:
            listed.unlink(missing_ok=True)
            limited.unlink(missing_ok=True)
        if result["returncode"] != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallFailed(result)
        staging.mkdir(exist_ok=True)
        with open(f"{target}.json", "w") as f:
            json.dump({"installed": [list(pair) for pair in result.get("installed") or []],
                       "substituted": {name: list(pair) for name, pair in
                                       (result.get("substituted") or {}).items()},
                       "ignored": {name: list(pair) for name, pair in
                                   (result.get("ignored") or {}).items()},
                       "yanked": list(result.get("yanked") or [])}, f)
        os.rename(staging, target)

    return str(target), recorded(target)
