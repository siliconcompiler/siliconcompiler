"""How far a reader has to click to find a page.

A strict build proves every link *resolves*. It says nothing about whether a
reader can *find* the page: a tutorial buried three clicks down a section index
builds exactly as green as one linked from the landing page. The audit that
prompted these tests measured the landing page and found nine pages one click
away and not a single tutorial among them, while the pages people actually
arrive looking for -- how to lint, how to simulate, how to bring their own
design -- sat behind a section index.

Reachability is measured from the reStructuredText rather than from built HTML
so that it runs offline on every pull request, in the same second as the rest of
the suite, instead of only after a full Sphinx build.
"""

import os.path
import re
from collections import deque

import pytest

from siliconcompiler.schema import docs


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)


DOCS_DIR = os.path.join(docs.sc_root, "docs")

#: The page a reader lands on.
ROOT = "index"

# A cross-reference role with either form: :ref:`label` or :ref:`Some text <label>`.
REF_ROLE = re.compile(r":ref:`([^`]+)`")
DOC_ROLE = re.compile(r":doc:`([^`]+)`")
#: An explicit label definition, e.g. ``.. _quickstart_guide:``
LABEL_DEF = re.compile(r"^\.\. _([A-Za-z0-9_.+-]+):\s*$", re.MULTILINE)
INCLUDE = re.compile(r"^\s*\.\. include::\s*(\S+)\s*$", re.MULTILINE)


def _docname(path):
    """Sphinx docname for a source path: docs-relative, no extension."""
    return os.path.relpath(path, DOCS_DIR)[:-len(".rst")].replace(os.sep, "/")


def _documents():
    """Every .rst document in the docs tree, as docnames."""
    found = []
    for dirpath, dirnames, filenames in os.walk(DOCS_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("_build", "__pycache__")]
        for name in filenames:
            if name.endswith(".rst"):
                found.append(_docname(os.path.join(dirpath, name)))
    return sorted(found)


def _read(docname):
    with open(os.path.join(DOCS_DIR, docname + ".rst"), encoding="utf-8") as f:
        return f.read()


def _source_of(docname):
    """The text of a document with any ``include``-d reStructuredText spliced in.

    ``index.rst`` includes ``user_guide/what_is_sc.rst``, so links written in
    that file are links a reader sees on the landing page. Counting them
    anywhere else would understate what the landing page offers.
    """
    text = _read(docname)
    for target in INCLUDE.findall(text):
        if not target.endswith(".rst"):
            continue
        base = DOCS_DIR if target.startswith("/") else os.path.dirname(
            os.path.join(DOCS_DIR, docname))
        path = os.path.normpath(os.path.join(base, target.lstrip("/")))
        if os.path.exists(path):
            text += "\n" + _read(_docname(path))
    return text


def _resolve(target, docname):
    """Resolve a toctree entry or :doc: target to a docname."""
    # "Title <target>" keeps only the target.
    if "<" in target and target.endswith(">"):
        target = target[target.index("<") + 1:-1]
    target = target.strip()
    if target.startswith("/"):
        return target.lstrip("/")
    return os.path.normpath(
        os.path.join(os.path.dirname(docname), target)).replace(os.sep, "/")


def _toctree_entries(docname, text):
    """Documents listed in ``toctree`` directives in this document."""
    entries = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != ".. toctree::":
            continue
        indent = len(line) - len(line.lstrip())
        for entry in lines[i + 1:]:
            if not entry.strip():
                continue
            entry_indent = len(entry) - len(entry.lstrip())
            if entry_indent <= indent:
                break                      # dedented out of the directive
            stripped = entry.strip()
            if stripped.startswith(":"):
                continue                   # a directive option, not an entry
            if stripped == "self":
                continue
            entries.append(_resolve(stripped, docname))
    return entries


def _label_map(documents):
    """Every explicit label, mapped to the document that defines it."""
    labels = {}
    for docname in documents:
        for label in LABEL_DEF.findall(_read(docname)):
            labels.setdefault(label, docname)
    return labels


def _graph():
    """Directed graph of documents, following toctrees and body cross-references."""
    documents = _documents()
    known = set(documents)
    labels = _label_map(documents)

    graph = {}
    for docname in documents:
        text = _source_of(docname)
        targets = set(_toctree_entries(docname, text))

        for match in DOC_ROLE.findall(text):
            targets.add(_resolve(match, docname))

        for match in REF_ROLE.findall(text):
            label = match
            if "<" in label and label.endswith(">"):
                label = label[label.index("<") + 1:-1]
            target = labels.get(label.strip())
            if target:
                targets.add(target)

        graph[docname] = {t for t in targets if t in known and t != docname}
    return graph


def _hops():
    """Click distance from the landing page to every reachable document."""
    graph = _graph()
    assert ROOT in graph, f"no {ROOT}.rst in {DOCS_DIR}"

    distance = {ROOT: 0}
    queue = deque([ROOT])
    while queue:
        current = queue.popleft()
        for target in sorted(graph[current]):
            if target not in distance:
                distance[target] = distance[current] + 1
                queue.append(target)
    return distance


def _tutorials():
    """Every tutorial page, taken from the directory rather than a hand-list."""
    tutorial_dir = os.path.join(DOCS_DIR, "user_guide", "tutorials")
    return sorted(
        _docname(os.path.join(tutorial_dir, name))
        for name in os.listdir(tutorial_dir)
        if name.endswith(".rst"))


# When this was first measured the landing page reached twelve pages in one click
# and not one of them was a tutorial; all nineteen tutorials sat at two hops,
# behind a section index. Giving the landing page a four-way signpost and a
# task-oriented directory took the one-hop reach to 36 and every tutorial to one
# hop.
#
# The floor is the measured value rather than a round number below it, so that
# losing a route is a test failure and not a rounding allowance. Raising it is
# welcome. Lowering it should come with a reason.
#
# Worth knowing when editing the landing page: it does not include
# `what_is_sc.rst` any more, so the routes to the schema and Python API pages come
# from the signpost's "Looking something up" panel. Removing that panel costs two
# one-hop routes.
MIN_ONE_HOP = 36


def test_every_tutorial_is_one_hop_from_the_landing_page():
    """A reader should not have to guess which section index hides a tutorial.

    Tutorials are the pages that answer "how do I actually do this", and they
    were the furthest thing from the landing page: reachable only by opening the
    User Guide first and scrolling past four other captions.
    """
    hops = _hops()
    buried = {t: hops.get(t) for t in _tutorials() if hops.get(t) != 1}

    assert not buried, (
        "tutorials that are not one click from the landing page "
        "(None means unreachable):\n  "
        + "\n  ".join(f"{name}: {distance}" for name, distance in buried.items()))


def test_help_pages_are_one_hop_from_the_landing_page():
    """The pages a stuck reader wants are the ones they cannot afford to hunt for."""
    hops = _hops()
    expected = [
        "user_guide/faq",
        "user_guide/howto",
        "user_guide/glossary",
        "user_guide/quickstart",
        "user_guide/installation",
        "user_guide/migration",
        "development_guide/contribution",
    ]
    missing = {name: hops.get(name) for name in expected if hops.get(name) != 1}

    assert not missing, (
        "help pages that are not one click from the landing page "
        "(None means unreachable):\n  "
        + "\n  ".join(f"{name}: {distance}" for name, distance in missing.items()))


def test_landing_page_reach_does_not_regress():
    """Guard the total, so a rewrite cannot quietly shrink the landing page."""
    hops = _hops()
    one_hop = sorted(name for name, distance in hops.items() if distance == 1)

    assert len(one_hop) >= MIN_ONE_HOP, (
        f"the landing page reaches {len(one_hop)} pages in one click, below the "
        f"floor of {MIN_ONE_HOP}. If a page was deliberately removed from the "
        f"landing page, lower MIN_ONE_HOP and say why.\n  "
        + "\n  ".join(one_hop))


def test_no_page_is_unreachable():
    """A page nothing links to is a page nobody reads.

    Sphinx catches a document missing from every *toctree*, but not one that is
    in a toctree whose own page nothing reaches.
    """
    hops = _hops()
    unreachable = [name for name in _documents() if name not in hops]

    assert not unreachable, (
        "documents no reader can reach from the landing page:\n  "
        + "\n  ".join(unreachable))
