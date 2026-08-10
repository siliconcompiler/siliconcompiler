import os.path
import re

from pathlib import PureWindowsPath
from typing import Optional

import siliconcompiler
from siliconcompiler import __version__ as sc_version

try:
    # setuptools_scm's full version, which records the commit for a dev build
    # ("0.38.3.dev153+g03290aacd"). sc_version is the last tag, which is not the
    # same thing between releases.
    from siliconcompiler._version import __version__ as sc_scm_version
except ImportError:  # pragma: no cover - only when not built by setuptools_scm
    sc_scm_version = sc_version


sc_root = os.path.dirname(os.path.dirname(os.path.abspath(siliconcompiler.__file__)))


def relpath(file):
    file = os.path.abspath(file)
    if file.startswith(sc_root):
        rel = PureWindowsPath(os.path.relpath(file, sc_root)).as_posix()
        # An in-tree virtual environment (a very common editable-install layout)
        # puts every installed package underneath sc_root, so a path check alone
        # would claim third-party files such as lambdapdk's and generate
        # siliconcompiler URLs for them that 404. Decline those so
        # resolve_codeurl falls through to the plugins, which know the real home
        # of each package.
        if any(part in ("site-packages", "dist-packages") for part in rel.split("/")):
            return None
        return rel
    return None


def _git_ref() -> str:
    """The git ref generated links should point at.

    A release tag is only correct when the docs were built from that release.
    Anything built between releases contains files the tag does not, so linking
    the tag 404s for them -- which is how the weekly link check found three
    dead example links pointing into ``v0.38.2``.
    """
    if os.getenv("READTHEDOCS"):
        if os.getenv("READTHEDOCS_VERSION") == "stable":
            # A stable build *is* the tag, so name it: readable, and permanent.
            return os.getenv("READTHEDOCS_GIT_IDENTIFIER", f"v{sc_version}")
        commit = os.getenv("READTHEDOCS_GIT_COMMIT_HASH")
        if commit:
            return commit

    # Off Read the Docs -- a CI link check, or a local build -- fall back to the
    # commit recorded in the dev version's local segment. A clean release has no
    # such segment, and its tag is then the right thing to link.
    match = re.search(r"\+g([0-9a-f]{7,40})", sc_scm_version)
    return match.group(1) if match else f"v{sc_version}"


def get_codeurl(file=None):
    base_url = \
        f"https://github.com/siliconcompiler/siliconcompiler/blob/{_git_ref()}"

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
