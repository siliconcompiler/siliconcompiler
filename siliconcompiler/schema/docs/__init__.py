import os.path

from pathlib import PureWindowsPath
from typing import Optional

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


def resolve_codeurl(file: str) -> Optional[str]:
    """
    Resolves a source file to a browsable URL.

    :func:`get_codeurl` is consulted first, so files inside the siliconcompiler tree
    always link to the siliconcompiler repository. Files outside that tree are handed
    to the ``siliconcompiler.docs`` ``linkcode`` plugins, in discovery order, until one
    claims the file.

    Args:
        file (str): Path to the source file.

    Returns:
        Optional[str]: The URL for the file, or None if nothing can resolve it.
    """
    from siliconcompiler.utils import get_plugins

    src_link = get_codeurl(file=file)
    if src_link:
        return src_link

    # Only scan for plugins once the built-in has declined the file, so the common case
    # does not pay for entry point discovery and plugin imports.
    for docs_link in get_plugins("docs", name="linkcode"):
        src_link = docs_link(file=file)
        if src_link:
            return src_link

    return None
