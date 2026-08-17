"""Generate ``llms.txt`` and ``llms-full.txt`` at build time.

Two audiences read this documentation and only one of them was designed for.
A code assistant asked "how do I compile a chip with SiliconCompiler?" answers
from whatever it absorbed during training, which is dominated by the pre-0.35
``Chip`` API -- and the site offers it nothing authoritative and cheap to fetch
that says otherwise. `llms.txt <https://llmstxt.org>`_ is the convention for
that: one small file at a predictable URL that states what the project is, what
the current idiom is, and where the rest lives.

Two files are written to the output root:

``llms.txt``
    A curated preamble followed by a generated index of every page, grouped by
    section, with absolute URLs. Small enough to fetch speculatively.

``llms-full.txt``
    The same preamble followed by the full text of every prose page, rendered to
    Markdown. One fetch instead of forty.

The preamble is hand-written -- ``docs/_llms/preamble.md`` -- because its value
is editorial: it is where the project says which API is current and, more
usefully, which names no longer exist. Negative information is what stops a
model emitting ``Chip()``, and nothing can generate it. The index and the body
are generated so they cannot drift from the site.

The generated reference tree is **linked but not inlined** in ``llms-full.txt``.
The schema reference alone is larger than the entire prose corpus and is far
better served by the machine-readable dump (``schema.json``, written by
``schemadump.py``) than by paragraphs of prose about parameters. The prose/
generated split is the same one ``searchrank.py`` uses for search ranking, and is
imported from there rather than repeated.
"""

import os
import posixpath
import urllib.parse

from docutils import nodes

from sphinx import addnodes
from sphinx.util import logging

from searchrank import is_generated

logger = logging.getLogger(__name__)

# Escape hatch for local iteration, honoured by schemadump.py too. Rendering every
# page costs around ten seconds, which is worth paying on a release build and not
# worth paying on the twentieth rebuild while editing one paragraph.
#
# An environment variable rather than a Sphinx config value on purpose: changing a
# config value invalidates the build cache and forces a full rebuild, which would
# cost far more than it saved.
SKIP_ENV = "SC_DOCS_SKIP_ARTIFACTS"

# Fallback when the builder has no canonical URL, i.e. every local build. Read
# the Docs sets html_baseurl per version, which is what the published files use.
FALLBACK_BASEURL = "https://docs.siliconcompiler.com/en/latest/"

PREAMBLE = os.path.join("_llms", "preamble.md")

# The published names, written into the root of the HTML output. Named rather than
# inlined at the call below because conf.py builds its linkcheck exemption from
# them: these files exist only in the built site, and linkcheck resolves a relative
# link against the *source* tree, so the links machine_readable.rst uses to reach
# them can never resolve there.
SHORT_OUTPUT = "llms.txt"
FULL_OUTPUT = "llms-full.txt"

# Human-readable names for the top-level sections, keyed by docname prefix.
# Anything not matched is grouped under "Other".
SECTIONS = (
    ("user_guide/tutorials/", "Tutorials"),
    ("user_guide/", "User guide"),
    ("development_guide/", "Advanced guide: building your own modules"),
    ("reference_manual/", "Reference (generated from the source tree)"),
)


def _section_of(docname):
    for prefix, title in SECTIONS:
        if docname.startswith(prefix):
            return title
    return "Other"


class _Markdown:
    """Render a resolved doctree to Markdown.

    Deliberately hand-rolled rather than borrowing Sphinx's ``TextBuilder``:
    constructing a second builder inside a running build means reaching into
    internals that carry no compatibility promise, and the output would be plain
    text where the consumers of these files expect Markdown.

    Every node type SiliconCompiler's prose actually uses is handled below.
    Anything else falls back to ``astext()``, so an unrecognised directive
    degrades to its own text rather than vanishing or raising.
    """

    # Nodes carrying no reader-facing text, or whose text is an artifact of the
    # build rather than content. ``index`` is Sphinx's, not docutils'.
    SKIP = (nodes.comment, nodes.system_message, nodes.raw, nodes.image,
            nodes.target, nodes.substitution_definition, nodes.problematic,
            addnodes.index, addnodes.highlightlang)

    def __init__(self, pageurl):
        # Sphinx writes internal link targets relative to the page they appear
        # on, so resolving them against that page's URL is what a browser does.
        self._pageurl = pageurl
        self._out = []

    # -- inline ----------------------------------------------------------

    def _inline(self, node):
        """Return the Markdown for a node's inline content."""
        if isinstance(node, nodes.Text):
            return node.astext()
        if isinstance(node, self.SKIP):
            return ""
        if isinstance(node, (nodes.literal, addnodes.literal_strong,
                             addnodes.literal_emphasis)):
            text = node.astext()
            # A backtick inside the text needs a longer fence around it.
            fence = "``" if "`" in text else "`"
            return f"{fence}{text}{fence}"
        if isinstance(node, nodes.strong):
            return f"**{self._children(node)}**"
        if isinstance(node, nodes.emphasis):
            return f"*{self._children(node)}*"
        if isinstance(node, nodes.reference):
            text = self._children(node)
            uri = node.get("refuri")
            if not uri:
                return text
            return f"[{text}]({self._absolute(uri)})"
        if isinstance(node, nodes.footnote_reference):
            return ""
        return self._children(node)

    def _children(self, node):
        return "".join(self._inline(child) for child in node.children)

    def _absolute(self, uri):
        """Turn a page-relative URI into an absolute one.

        ``urljoin`` handles every case the same way a browser does: already
        absolute URLs and ``mailto:`` pass through, ``../`` segments resolve, and
        a bare ``#anchor`` gains the page it was written on -- which matters here
        because these files concatenate pages and an orphaned fragment would
        point at nothing.
        """
        return urllib.parse.urljoin(self._pageurl, uri)

    # -- block -----------------------------------------------------------

    def _emit(self, text=""):
        self._out.append(text)

    def render(self, node, depth=1):
        """Walk a section-bearing node, emitting Markdown for its children."""
        for child in node.children:
            self._block(child, depth)
        return "\n".join(self._out).strip() + "\n"

    def _block(self, node, depth):
        if isinstance(node, self.SKIP):
            return

        if isinstance(node, nodes.section):
            for child in node.children:
                self._block(child, depth + 1)
            return

        if isinstance(node, nodes.title):
            # Markdown has six heading levels; deeper nesting flattens onto the
            # last one rather than emitting an invalid run of hashes.
            self._emit(f"\n{'#' * min(depth, 6)} {self._children(node)}\n")
            return

        if isinstance(node, nodes.literal_block):
            language = node.get("language", "")
            if language in ("default", "none"):
                language = ""
            self._emit(f"```{language}\n{node.astext()}\n```\n")
            return

        if isinstance(node, (nodes.bullet_list, nodes.enumerated_list)):
            self._list(node, depth, ordered=isinstance(node, nodes.enumerated_list))
            self._emit()
            return

        if isinstance(node, nodes.definition_list):
            for item in node.children:
                term = "".join(self._children(c) for c in item.children
                               if isinstance(c, nodes.term))
                self._emit(f"**{term}**\n")
                for c in item.children:
                    if isinstance(c, nodes.definition):
                        self._indented(c, depth)
            return

        if isinstance(node, nodes.table):
            self._table(node)
            return

        if isinstance(node, (nodes.note, nodes.warning, nodes.tip,
                             nodes.important, nodes.caution, nodes.admonition,
                             nodes.attention, nodes.hint, addnodes.seealso)):
            self._admonition(node, depth)
            return

        # ``compact_paragraph`` is a paragraph subclass, and resolved toctrees are
        # built from them, so this branch renders the nav lists too.
        if isinstance(node, (nodes.paragraph, nodes.line_block)):
            text = self._children(node).strip()
            if text:
                self._emit(f"{text}\n")
            return

        if isinstance(node, (nodes.compound, nodes.block_quote, nodes.container,
                             nodes.topic, nodes.sidebar, nodes.field_list,
                             nodes.field, nodes.field_body, nodes.line,
                             nodes.rubric, nodes.transition, nodes.list_item,
                             nodes.definition, nodes.entry)):
            for child in node.children:
                self._block(child, depth)
            return

        # Unrecognised: keep the words rather than dropping them.
        text = node.astext().strip()
        if text:
            self._emit(f"{text}\n")

    def _list(self, node, depth, ordered):
        for number, item in enumerate(node.children, start=1):
            marker = f"{number}." if ordered else "-"
            body = _Markdown(self._pageurl).render(item, depth).strip()
            if not body:
                continue
            lines = body.splitlines()
            self._emit(f"{marker} {lines[0]}")
            for line in lines[1:]:
                self._emit(f"  {line}" if line else "")

    def _indented(self, node, depth):
        body = _Markdown(self._pageurl).render(node, depth).strip()
        for line in body.splitlines():
            self._emit(f"  {line}" if line else "")
        self._emit()

    def _admonition(self, node, depth):
        label = node.get("names") or [type(node).__name__]
        body = _Markdown(self._pageurl).render(node, depth).strip()
        # Blockquote the whole thing so the boundary survives concatenation.
        self._emit(f"> **{str(label[0]).capitalize()}**")
        for line in body.splitlines():
            self._emit(f"> {line}" if line else ">")
        self._emit()

    def _table(self, node):
        rows = []
        header = 0
        for group in node.findall(nodes.tgroup):
            for part in group.children:
                if isinstance(part, (nodes.thead, nodes.tbody)):
                    for row in part.children:
                        cells = [" ".join(self._cell(entry).split())
                                 for entry in row.children]
                        rows.append(cells)
                    if isinstance(part, nodes.thead):
                        header = len(rows)
        if not rows:
            return

        # A table whose every cell renders empty carries nothing. This is not
        # hypothetical: `list-table`s used purely to lay out screenshots side by
        # side (tutorials/emails.rst) lose all their content here, because images
        # are skipped, and would otherwise emit rows of bare pipes.
        if not any(cell for row in rows for cell in row):
            return

        width = max(len(row) for row in rows)

        # Markdown requires a delimiter row, and a table built by `list-table`
        # without `:header-rows:` has no thead to put one after. Synthesise an
        # empty header rather than promoting the first data row, which would
        # silently relabel content as a heading.
        if not header:
            self._emit("| " + " | ".join([""] * width) + " |")
            self._emit("|" + "|".join([" --- "] * width) + "|")

        for index, row in enumerate(rows):
            padded = row + [""] * (width - len(row))
            self._emit("| " + " | ".join(padded) + " |")
            if index + 1 == header:
                self._emit("|" + "|".join([" --- "] * width) + "|")
        self._emit()

    def _cell(self, entry):
        return _Markdown(self._pageurl).render(entry).strip()


def _pageurl(baseurl, docname):
    """Absolute URL of a built page."""
    return posixpath.join(baseurl, f"{docname}.html")


def _ordered_docnames(env):
    """Every reachable docname, in navigation order.

    Depth-first over the toctrees from the root document, which is the order a
    reader meets the pages. Falls back to appending anything unreachable, so a
    page missing from the nav still appears rather than being silently dropped.
    """
    seen = []

    def walk(docname):
        if docname in seen:
            return
        seen.append(docname)
        for child in env.toctree_includes.get(docname, []):
            walk(child)

    walk(env.config.root_doc)
    for docname in sorted(env.all_docs):
        if docname not in seen:
            seen.append(docname)
    return seen


def _title(env, docname):
    title = env.titles.get(docname)
    return title.astext() if title else docname


def _summary(doctree):
    """First sentence of a page's first real paragraph, or ``None``."""
    for paragraph in doctree.traverse(nodes.paragraph):
        text = " ".join(paragraph.astext().split())
        if len(text) < 20:
            continue
        # Cut at the first sentence end that is not an abbreviation or a
        # version number.
        for index in range(len(text) - 1):
            if text[index] == "." and text[index + 1] == " " \
                    and not text[index - 1].isdigit():
                return text[:index + 1]
        return text if len(text) <= 300 else text[:297].rsplit(" ", 1)[0] + "..."
    return None


# Sphinx's smartquotes transform rewrites straight quotes and ``--`` into
# typographic characters, which is right for a rendered page and wrong for a
# plain-text file: consumers of these files diff them, grep them, and paste
# snippets out of them, and a curly apostrophe in a code-adjacent string is a
# small trap for no benefit.
#
# Only the substitutions smartquotes makes are undone. Box-drawing characters
# (the directory trees in ``directories.rst``), arrows and Greek letters are
# content the author chose, they appear inside literal blocks that smartquotes
# never touches, and mangling them would corrupt the page.
_TYPOGRAPHIC = {
    "‘": "'", "’": "'",           # single quotes
    "“": '"', "”": '"',           # double quotes
    "–": "--", "—": "--",         # en and em dash, both from ``--``
    "…": "...",                        # ellipsis
    " ": " ",                          # non-breaking space
    "‑": "-",                          # non-breaking hyphen
}

_ASCII = str.maketrans(_TYPOGRAPHIC)


def _write(outdir, name, text):
    path = os.path.join(outdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.translate(_ASCII))
    return path


def generate(app, exception):
    # HTML only: these files are published from the site root, so a latex,
    # linkcheck or dummy build has nowhere to put them and no reason to pay for
    # them. Note this is the builder *name*, so switching the site to `dirhtml`
    # would need this updated.
    if exception is not None or app.builder.name != "html":
        return
    if os.environ.get(SKIP_ENV):
        logger.info("skipping llms.txt (%s is set)", SKIP_ENV)
        return

    baseurl = app.config.html_baseurl or FALLBACK_BASEURL
    if not baseurl.endswith("/"):
        baseurl += "/"

    preamble_path = os.path.join(app.srcdir, PREAMBLE)
    if not os.path.exists(preamble_path):
        logger.warning("llms.txt preamble is missing: %s", preamble_path)
        return
    with open(preamble_path, encoding="utf-8") as f:
        preamble = f.read().rstrip()

    docnames = _ordered_docnames(app.env)

    index = {}
    bodies = []
    for docname in docnames:
        page_url = _pageurl(baseurl, docname)
        try:
            doctree = app.env.get_and_resolve_doctree(docname, app.builder)
        except Exception as e:                                 # pragma: no cover
            logger.warning("llms.txt could not read %s: %s", docname, e)
            continue

        title = _title(app.env, docname)
        entry = f"- [{title}]({page_url})"
        summary = _summary(doctree)
        if summary:
            entry += f": {summary}"
        index.setdefault(_section_of(docname), []).append(entry)

        # The generated reference is linked from llms.txt but not inlined: it is
        # larger than everything else combined and schema.json serves it better.
        if not is_generated(docname):
            body = _Markdown(page_url).render(doctree)
            bodies.append(f"\n\n---\n\nSource: {page_url}\n\n{body}")

    listing = []
    seen = set()
    for _, section in SECTIONS + (("", "Other"),):
        entries = index.get(section)
        if not entries or section in seen:
            continue
        seen.add(section)
        listing.append(f"\n## {section}\n\n" + "\n".join(entries))

    short = f"{preamble}\n\n" + "\n".join(listing) + "\n"
    _write(app.outdir, SHORT_OUTPUT, short)

    full = (f"{preamble}\n\n"
            "The remainder of this file is the full text of every hand-written "
            "page on the documentation site. The generated reference -- the "
            "schema, the Python API, the CLI apps and the module catalogues -- "
            f"is not included; see {posixpath.join(baseurl, 'schema.json')} for "
            "the machine-readable schema and the links above for the rest.\n"
            + "".join(bodies) + "\n")
    _write(app.outdir, FULL_OUTPUT, full)

    logger.info("wrote llms.txt (%d pages indexed) and llms-full.txt (%d pages, %.0f kB)",
                len(docnames), len(bodies), len(full) / 1024)


def setup(app):
    app.connect("build-finished", generate)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
