"""Generate the example gallery from ``examples/`` at build time.

``examples/`` holds working, tested designs, and until now nothing on the site
pointed at them: a reader who wanted to see real code had to go to GitHub and
guess. Seven of the directories had no reference from any page at all.

A hand-written index would fix that once. This directive fixes it permanently,
because it enumerates the directory rather than a list someone has to remember to
update -- a new example appears in the gallery by existing, and an undocumented
one **fails the build** rather than quietly staying invisible. That last property
is the point; the gap this closes was created by exactly that kind of silence.

Each example describes itself in the module docstring of its entry script, which
is resolved in this order:

1. ``make.py``
2. ``<directory>.py``
3. the only ``.py`` in the directory
4. the only ``.py`` carrying a module docstring

Rule 4 covers directories holding several runnable scripts (``sva_sby``,
``oh_experiments``): documenting one at module level marks it as the way in,
without inventing a metadata file to keep in sync.

The description is that script's module docstring, or -- because most of these
examples already carry their explanation there -- the docstring of a top-level
``main()``. Either is read; neither has to be moved.

The description's first line is the summary. A trailing ``Requires:`` line, if
present, is pulled out and rendered as the tools the example needs::

    \"\"\"Formal property checking with SymbiYosys.

    Proves the SVA assertions carried by a small FIFO.

    Requires: sby, yosys
    \"\"\"

Docstrings are read with :mod:`ast`, never by importing: examples import EDA
tool drivers and construct designs, and the docs build has no business running
any of that.
"""

import ast
import os

from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from siliconcompiler.schema.docs import get_codeurl

# Not examples: build output, caches, and the shared requirements file.
SKIP = {"__pycache__", "build"}


def _entry_script(directory):
    """Return the path of the script that describes this example, or None."""
    scripts = sorted(f for f in os.listdir(directory) if f.endswith(".py"))
    if not scripts:
        return None

    name = os.path.basename(directory)
    for preferred in ("make.py", f"{name}.py"):
        if preferred in scripts:
            return os.path.join(directory, preferred)

    if len(scripts) == 1:
        return os.path.join(directory, scripts[0])

    documented = [f for f in scripts
                  if ast.get_docstring(_parse(os.path.join(directory, f)))]
    if len(documented) == 1:
        return os.path.join(directory, documented[0])

    return None


def _parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _description(tree):
    """The module docstring, or a top-level main()'s, or None."""
    doc = ast.get_docstring(tree)
    if doc:
        return doc

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return ast.get_docstring(node)

    return None


def _split_requires(doc):
    """Split a docstring into (summary, body, requires)."""
    lines = doc.strip().split("\n")
    summary, rest = lines[0].strip(), lines[1:]

    requires = None
    kept = []
    consuming = False
    for line in rest:
        if line.strip().lower().startswith("requires:"):
            requires = line.split(":", 1)[1].strip()
            consuming = True
            continue
        # A "Requires:" too long for one line wraps like any other field. Fold
        # continuations in rather than leaving half of it stranded in the body.
        if consuming and line.strip():
            requires = f"{requires} {line.strip()}".strip()
            continue
        consuming = False
        kept.append(line)

    return summary, "\n".join(kept).strip(), requires


class ScExamples(SphinxDirective):
    """Render one entry per directory in ``examples/``."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        _, root = self.env.relfn2path(self.arguments[0])
        root = os.path.abspath(root)

        # Depend on the directory itself, not only on the scripts inside it.
        # Adding an example changes the directory's mtime but no file this page
        # already knows about, so without this an incremental build would keep
        # serving the cached page and the "new examples appear automatically"
        # guarantee would quietly not hold.
        self.env.note_dependency(root)
        self.env.note_dependency(__file__)

        directories = sorted(
            os.path.join(root, d) for d in os.listdir(root)
            if d not in SKIP and os.path.isdir(os.path.join(root, d)))

        content = ViewList()
        for directory in directories:
            name = os.path.basename(directory)
            script = _entry_script(directory)
            if script is None:
                raise self.error(
                    f"examples/{name} has no entry script to describe it. Add a "
                    "module docstring to make.py, to a script named after the "
                    "directory, or to exactly one script in it.")

            self.env.note_dependency(script)
            doc = _description(_parse(script))
            if not doc:
                raise self.error(
                    f"examples/{name}: {os.path.basename(script)} documents "
                    "neither the module nor main(), so the gallery has nothing "
                    "to say about it. The first line becomes the summary.")

            summary, body, requires = _split_requires(doc)
            # get_codeurl points at the file; the gallery links the directory,
            # and GitHub 301s /blob/<ref>/<dir> to /tree/. Link the target.
            url = os.path.dirname(get_codeurl(script)).replace("/blob/", "/tree/", 1)

            content.append(f".. _example-{name}:", script)
            content.append("", script)
            content.append(f"``{name}``", script)
            content.append("-" * (len(name) + 4), script)
            content.append("", script)
            content.append(summary, script)
            content.append("", script)
            if body:
                for line in body.split("\n"):
                    content.append(line, script)
                content.append("", script)
            if requires:
                content.append(f":Requires: {requires}", script)
                content.append("", script)
            content.append(
                f":Source: `examples/{name} <{url}>`__ "
                f"(entry point ``{os.path.basename(script)}``)", script)
            content.append("", script)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, content, node)
        return node.children


def setup(app):
    app.add_directive("scexamples", ScExamples)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
