import os.path

from pathlib import PureWindowsPath

import siliconcompiler
from siliconcompiler import __version__ as sc_version


sc_root = os.path.dirname(os.path.dirname(os.path.abspath(siliconcompiler.__file__)))


def relpath(file):
    file = os.path.abspath(file)
    if file.startswith(sc_root):
        return PureWindowsPath(os.path.relpath(file, sc_root)).as_posix()
    return None


def get_codeurl(file=None):
    blob = f"v{sc_version}"
    if os.getenv("READTHEDOCS"):
        # Use git commit
        blob = os.getenv("READTHEDOCS_GIT_COMMIT_HASH", blob)
        if os.getenv("READTHEDOCS_VERSION") == "stable":
            # use git identifier name
            blob = os.getenv("READTHEDOCS_GIT_IDENTIFIER", blob)

    base_url = f"https://github.com/siliconcompiler/siliconcompiler/blob/{blob}"

    if not file:
        return base_url

    if os.path.isabs(file):
        file = relpath(file)
        if not file:
            return None

    return f"{base_url}/{file}"
