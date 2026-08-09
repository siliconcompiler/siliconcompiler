"""Prose defects that a strict Sphinx build cannot catch.

``-W`` fails the build on anything Sphinx considers a warning, but some of the
worst documentation defects are perfectly valid reStructuredText that simply
means something other than what the author intended. Those need their own check.
"""

import os.path
import re

import pytest

from siliconcompiler.schema import docs


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)


DOCS_DIR = os.path.join(docs.sc_root, "docs")


def _sources():
    for dirpath, dirnames, filenames in os.walk(DOCS_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("_build", "__pycache__")]
        for name in sorted(filenames):
            if name.endswith((".rst", ".inc")):
                yield os.path.join(dirpath, name)


# `Some text <a_label>`_ is an *external* hyperlink whose target is a relative
# URL, not a cross-reference. Docutils accepts it silently and Sphinx emits no
# warning, so it renders as a link to a page that does not exist. The author
# almost always meant :ref:`Some text <a_label>`. A genuine relative link
# carries a dot, a slash or a scheme, so requiring none of those keeps this
# from firing on real URLs.
BAD_REF = re.compile(r"`[^`<>\n]+ <([A-Za-z0-9_-]+)>`_")


def test_no_external_link_syntax_pointing_at_internal_labels():
    """Catch `text <label>`_ that should be :ref:`text <label>`.

    Six of these shipped to the live installation page and produced 404s across
    many releases without ever emitting a build warning.
    """
    found = []
    for path in _sources():
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                for match in BAD_REF.finditer(line):
                    rel = os.path.relpath(path, docs.sc_root)
                    found.append(f"{rel}:{lineno}: {match.group(0)}"
                                 f"  -> did you mean :ref:`... <{match.group(1)}>`?")

    assert not found, (
        "external hyperlink syntax used with what looks like an internal label; "
        "these render as broken relative URLs:\n  " + "\n  ".join(found))


def test_no_markdown_link_syntax():
    """Catch [text](url), which RST renders as literal brackets and parens.

    One of these sat on the first screen of the installation page across many
    releases, alongside the correct RST form of the same link 130 lines later.
    """
    markdown_link = re.compile(r"\[[^\]\n]+\]\((?:https?://|\.{0,2}/)[^)\n]+\)")
    found = []
    for path in _sources():
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                match = markdown_link.search(line)
                if match:
                    rel = os.path.relpath(path, docs.sc_root)
                    found.append(f"{rel}:{lineno}: {match.group(0)}")

    assert not found, (
        "Markdown link syntax in reStructuredText renders as literal text; "
        "use `text <url>`_ instead:\n  " + "\n  ".join(found))
