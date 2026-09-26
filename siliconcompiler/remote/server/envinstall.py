'''
Installing a node's Python environment where the node runs, on the host.

Where nodes run on a host that may reach an index -- this server without
containers -- a node's environment file is installed there, before the flow
starts, into a cache kept per user (surface D131: the deployment's choice, and
not visible on the wire). A deployment that runs containers builds a derived
image instead, which this server does not do yet.

🔴 **The uploaded file is never handed to pip.** It is parsed against the format
again and a file of this server's own is written from what parsed, so a line pip
would read one way and the grammar another has no route through. **Wheels only**
(`--only-binary :all:`): installing from source runs the package's own code. The
result goes on the tool's `PYTHONPATH` through a `site` link beside the node's
file, and never on SiliconCompiler's own.
'''

import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import uuid

from pathlib import Path
from typing import List

from siliconcompiler.remote import environment

__all__ = ["install", "install_all"]


def install_all(project, job_dir: Path, logger) -> List[str]:
    '''Every node's environment, installed and linked. Returns the nodes.

    Raises RuntimeError naming the node when one will not install: on the host
    that is the run failing, since there is no `staging` to refuse it from.
    '''
    from siliconcompiler.utils.paths import cachedir

    top = Path(job_dir) / environment.ROOT
    if not top.is_dir():
        return []

    root = Path(cachedir(project)) / "python-env"
    installed = []
    for path in sorted(top.glob(f"*/*/{environment.FILENAME}")):
        step, index = path.parent.parent.name, path.parent.name
        try:
            parsed = environment.parse(path.read_bytes())
        except environment.EnvironmentFileError as e:
            raise RuntimeError(f"{step}/{index}: its Python environment file: {e}") from None
        if not parsed.pins:
            continue
        target = install(parsed, root, logger, f"{step}/{index}")

        link = path.parent / environment.SITE
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target, target_is_directory=True)
        installed.append(f"{step}/{index}")
    return installed


def install(parsed: environment.Environment, root: Path, logger, node: str) -> str:
    '''One environment into a directory of its own, built once and shared by
    every node of this user asking for the same set.

    Keyed by this Python, this platform and the file this server writes, and
    built under a lock beside it and moved into place whole, so a directory
    that exists is one that is finished.
    '''
    from fasteners import InterProcessLock

    text = environment.render(parsed.pins, parsed.index_url, parsed.extra_index_urls,
                              header="Written by sc-server from what the job's file "
                                     "declared; the file itself is never installed.")
    tag = sys.implementation.cache_tag
    key = hashlib.sha256(json.dumps({
        "python": tag, "platform": sysconfig.get_platform(), "file": text,
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
        logger.info(f"Installing {node}'s Python environment into {target}: "
                    f"{', '.join(str(pin) for pin in parsed.pins)}")
        command = [sys.executable, "-m", "pip", "install", "--only-binary", ":all:",
                   "--no-input", "--disable-pip-version-check",
                   "--target", str(staging), "-r", str(written)]
        try:
            done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, text=True)
        finally:
            written.unlink(missing_ok=True)
        if done.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            tail = "\n".join(done.stdout.strip().splitlines()[-20:])
            raise RuntimeError(
                f"{node}: its Python environment would not install for "
                f"{tag} on {sysconfig.get_platform()}:\n{tail}")
        os.rename(staging, target)

    return str(target)
