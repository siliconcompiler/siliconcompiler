# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import inspect
import importlib
import json
import sys

import os
import os.path

from datetime import date

sc_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sc_root)
import siliconcompiler  # noqa E402
sys.path.insert(0, os.path.join(sc_root, 'docs', '_ext'))

from siliconcompiler.schema.docs import get_codeurl, resolve_codeurl  # noqa E402


# -- Project information -----------------------------------------------------

project = 'SiliconCompiler'
copyright = f'2020-{date.today().year}, Zero ASIC'
author = 'SiliconCompiler Authors'

version = siliconcompiler.__version__
release = version

# Inject the authors list from _metadata.py as a variable |authors| that can be
# inserted into rst.
rst_epilog = f"""
.. |authors| replace:: {', '.join(siliconcompiler._metadata.authors)}
"""

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.imgconverter',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.graphviz',
    "sphinx.ext.linkcode",
    'siliconcompiler.schema.docs.schemagen',
    'clientservergen',
    'requirements',
    'installgen',
    'graphgen'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '.venv/**']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'friendly'

suppress_warnings = []

# Resolve standard-library types so they link to the Python documentation
# instead of rendering as dead text.
#
# Deliberately limited to one mapping. An unreachable inventory logs a warning
# with no subtype, so it cannot be filtered with suppress_warnings, and with
# SPHINXOPTS set to -W that turns a transient network failure into a failed docs
# build. Every additional mapping is another host that can take the build down,
# so a new one needs to earn its keep: packaging and pandas were tried and
# dropped, resolving one name between them.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}
intersphinx_timeout = 15

# Diagrams are kept as .dot sources and rendered at build time by
# sphinx.ext.graphviz, so they can be edited without anyone remembering to re-run
# `dot` and commit the result. SVG rather than the default PNG: it stays sharp at
# any zoom and the text in it is selectable and searchable.
graphviz_output_format = 'svg'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

# Read the Docs serves every tag and branch at its own URL, so search engines
# index them all. Without a canonical link, a query for "siliconcompiler install"
# can land a reader on a years-old version -- which matters more than usual here,
# because the pre-0.3x API is entirely different from the current one and nothing
# on the page says so.
#
# Read the Docs injects this per build; locally it is unset, which disables the
# tag rather than emitting a wrong one.
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")

# Version slug of the build ("latest", "stable", or a tag such as "v0.38.2").
_rtd_version = os.environ.get("READTHEDOCS_VERSION", "")

_docs_url = "https://docs.siliconcompiler.com/en"

html_theme_options = {
    "collapse_navigation": True,
    "show_toc_level": 2,   # this automatically displays two levels
    "logo": {
        "image_light": 'sc_logo_with_text.png',
        "image_dark": 'sc_logo_with_text.png',
    },
    "github_url": "https://github.com/siliconcompiler/siliconcompiler",  # these are top right

    # Add light/dark mode and documentation version switcher:
    "navbar_end": ["theme-switcher", "version-switcher", "navbar-icon-links"],
    "footer_start": ["copyright", "version"],

    # The switcher list is served from one place -- the stable build -- so every
    # version, including this one, offers the same choices. See write_switcher().
    "switcher": {
        "json_url": f"{_docs_url}/stable/_static/switcher.json",
        # Matches an entry below to highlight the current version in the
        # dropdown. Tagged builds carry a real version; the dev branch is
        # published as "latest" and matches on the slug instead.
        "version_match": "latest" if _rtd_version == "latest" else version,
    },
    # Do NOT fetch json_url at build time. The theme warns when it cannot reach
    # the URL, and SPHINXOPTS sets -W, so a transient network failure would fail
    # the build. The switcher itself is populated client-side and is unaffected.
    # Same reasoning as the single intersphinx mapping above.
    "check_switcher": False,

    # Warn readers who land on anything other than the current release. The
    # banner text is chosen by comparing this build's version against the
    # "preferred" entry in switcher.json.
    "show_version_warning_banner": True,
}


def write_switcher(app, exception):
    """Emit the version switcher list into the build output.

    Generated rather than checked in so that the "preferred" version is always
    the version that actually built it. ``json_url`` points at the stable build's
    copy, so the file everyone fetches is written by the stable tag and names the
    real current release -- no release-checklist step to forget, which is the
    failure mode this whole audit is about.
    """
    if exception is not None or app.builder.name != "html":
        return

    switcher = [
        {
            "name": f"{version} (stable)",
            "version": version,
            "url": f"{_docs_url}/stable/",
            "preferred": True,
        },
        {
            "name": "dev",
            "version": "latest",
            "url": f"{_docs_url}/latest/",
        },
    ]

    static = os.path.join(app.outdir, "_static")
    os.makedirs(static, exist_ok=True)
    with open(os.path.join(static, "switcher.json"), "w") as f:
        json.dump(switcher, f, indent=2)


def setup(app):
    app.connect("build-finished", write_switcher)

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.


html_sidebars = {
  "index": []
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_title = "%s v%s Manual" % (project, version)
html_static_path = ['_static']

html_css_files = [
    'css/custom.css',
]

# Rank hand-written prose above the auto-generated reference tree. See the
# comment block in the scorer itself for why this is needed.
html_search_scorer = '_static/search_scorer.js'
html_context = {"default_mode": "light"}
html_use_modindex = True
html_copy_source = False
html_domain_indices = False
html_file_suffix = '.html'


plot_html_show_formats = False
plot_html_show_source_link = False

# -- Options for Latex output ------------------------------------------------

# Allow linebreaks on underscores (fixes long cell names running past end of
# table cells)
latex_preamble = r"""\newcommand{\origunderscore}{}
\let\origunderscore\_
\renewcommand{\_}{\allowbreak\origunderscore}
\setcounter{tocdepth}{4}
"""

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).

latex_elements = {
    'extraclassoptions': 'openany,oneside',  # Don't add blank pages after some chapters
    'preamble': latex_preamble
}

latex_use_modindex = False

# Some vendor documentation sites are slow; 5s produced spurious timeouts.
linkcheck_timeout = 15

# External links flake, so linkcheck runs on a schedule rather than per-PR --
# see .github/workflows/docs_linkcheck.yml.
linkcheck_retries = 2

# GitHub rewrites Markdown heading anchors to "user-content-*" in the HTML it
# serves and restores the original ids client-side. linkcheck fetches the raw
# HTML, so it can never resolve an anchor into a README and reports every one as
# broken. Check that those pages exist, but not their fragments.
linkcheck_anchors_ignore_for_url = [
    r"https://github\.com/.*",
]

# Being rate-limited by a host is not a broken link; back off and retry rather
# than failing the run.
linkcheck_rate_limit_timeout = 60.0

# Skip the auto-generated "File: <source>.py" links emitted by autodoc/linkcode
# and the schema generators. There are ~1100 of them, they are all mechanically
# constructed by get_codeurl() from a single version tag, and hammering
# github.com with them is what gets a linkcheck run rate-limited before it
# reaches anything interesting.
#
# The install-script links (.sh) are deliberately *not* skipped even though they
# are generated the same way: there are only ~130, they exercise the same
# version tag, and a stale entry in the install table is user-facing.
linkcheck_ignore = [
    r"https://github\.com/siliconcompiler/[^/]+/blob/v[0-9][^\s]*\.py(#L\d+(-L\d+)?)?$",
]

# Modified from: https://github.com/readthedocs/sphinx-autoapi/issues/202#issuecomment-1048104024
code_url = get_codeurl()


def linkcode_resolve(domain, info):
    # Non-linkable objects from the starter kit in the tutorial.
    if domain != "py":
        return None

    assert domain == "py", "expected only Python objects"

    mod = importlib.import_module(info["module"])
    if "." in info["fullname"]:
        objname, attrname = info["fullname"].split(".")
        obj = getattr(mod, objname)
        try:
            # object is a method of a class
            obj = getattr(obj, attrname)
        except AttributeError:
            # object is an attribute of a class
            return None
    else:
        obj = getattr(mod, info["fullname"])

    try:
        file = inspect.getsourcefile(obj)
        lines = inspect.getsourcelines(obj)
    except TypeError:
        # e.g. object is a typing.Union
        return None

    path = resolve_codeurl(file)

    if path:
        start, end = lines[1], lines[1] + len(lines[0]) - 1

        return f"{path}#L{start}-L{end}"
    return None
