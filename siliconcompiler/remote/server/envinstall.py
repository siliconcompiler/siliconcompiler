'''
Installing a node's Python environment on the host, while the job is staging.

Where nodes run on this host -- this server without containers, dispatching
locally -- each executed node's environment file is installed here while the
job is `staging`, into a cache kept per user, so a line that will not install
rejects the job before any node runs rather than failing the run. A deployment
that runs containers builds a derived image instead -- `envbuild` -- with the
same install, `pipbuild`.

🔴 **The uploaded file is never handed to pip.** It is parsed against the format
again and a file of this server's own is written from what parsed, so a line pip
would read one way and the grammar another has no route through. **Wheels only**:
a source distribution builds only in the isolated builder. **From the
deployment's `package_indexes`**, never an index a job names. What this Python
already holds for the job's `requires.python` is never installed a second time
-- see `pipbuild`. The result goes on the tool's `PYTHONPATH` through a `site`
link beside the node's file, and never on SiliconCompiler's own.
'''

import hashlib
import json
import os
import shutil
import sys
import sysconfig
import uuid

from pathlib import Path
from typing import Any, Dict, List, Tuple

from siliconcompiler.remote import environment

__all__ = ["InstallFailed", "HEADER", "install", "install_all"]


HEADER = ("Written by sc-server from what the job's file declared; the file itself "
          "is never installed.")


class InstallFailed(RuntimeError):
    '''A node's environment that did not install. ``result`` is pipbuild's
    record, ``text`` the file this server wrote.'''

    def __init__(self, node: Tuple[str, str], text: str, result: Dict[str, Any]):
        self.node, self.text, self.result = node, text, result
        super().__init__(
            f"{node[0]}/{node[1]}: its Python environment would not install for "
            f"{result.get('python')} on {result.get('platform')}:\n"
            f"{result.get('tail', '')}")


def install_all(job_dir: Path, root: Path, logger, nodes, constrain=(),
                indexes=()) -> List[Tuple[str, str]]:
    '''Each of ``nodes`` that carries an environment file, installed into
    ``root`` and linked beside its file. Returns the nodes installed.

    ``constrain`` is what the job's `requires.python` names: each is pinned to
    the version this host holds. Raises InstallFailed for the first node that
    will not install.
    '''
    installed = []
    for step, index in sorted(nodes):
        path = Path(job_dir) / environment.path_for(step, index)
        if not path.is_file():
            continue
        parsed = environment.parse(path.read_bytes())
        if not parsed.pins:
            continue
        target = install(parsed, root, logger, (step, index), constrain, indexes)

        link = Path(job_dir) / environment.site_path(step, index)
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target, target_is_directory=True)
        installed.append((step, index))
    return installed


def install(parsed: environment.Environment, root: Path, logger, node: Tuple[str, str],
            constrain=(), indexes=()) -> str:
    '''One environment into a directory of its own, built once and shared by
    every node of this user asking for the same set.

    Keyed by this Python, this platform, the constraints and the indexes --
    the install adds to what those pin and comes from where they say, so both
    are part of what the result means -- and the file this server writes.
    Built under a lock beside it and moved into place whole, so a directory
    that exists is one that is finished.
    '''
    from fasteners import InterProcessLock

    from siliconcompiler.remote.server import pipbuild

    text = environment.render(parsed.pins, header=HEADER)
    tag = sys.implementation.cache_tag
    key = hashlib.sha256(json.dumps({
        "python": tag, "platform": sysconfig.get_platform(),
        "constraints": pipbuild.constraints(constrain), "indexes": list(indexes),
        "file": text,
    }).encode()).hexdigest()[:16]
    target = Path(root) / f"{tag}-{key}"
    if target.is_dir():
        return str(target)

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with InterProcessLock(f"{target}.lock"):
        if target.is_dir():
            return str(target)

        staging = Path(f"{target}.{uuid.uuid4().hex}")
        written = Path(f"{staging}.txt")
        written.write_text(text)
        logger.info(f"Installing {node[0]}/{node[1]}'s Python environment into {target}: "
                    f"{', '.join(str(pin) for pin in parsed.pins)}")
        try:
            result = pipbuild.install(str(written), str(staging), constrain=constrain,
                                      indexes=indexes)
        finally:
            written.unlink(missing_ok=True)
        if result["returncode"] != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallFailed(node, text, result)
        for name, (asked, got) in (result.get("substituted") or {}).items():
            logger.info(f"{node[0]}/{node[1]}: {name}=={asked} does not install here; "
                        f"{got} from its release line was installed instead")
        # Nothing to install is still an environment: the image held it all.
        staging.mkdir(exist_ok=True)
        os.rename(staging, target)

    return str(target)
