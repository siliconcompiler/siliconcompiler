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
import sys

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
    "sphinx.ext.linkcode",
    'siliconcompiler.schema.docs.schemagen',
    'clientservergen',
    'requirements',
    'installgen'
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

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

html_theme_options = {
    "collapse_navigation": True,
    "show_toc_level": 2,   # this automatically displays two levels
    "logo": {
        "image_light": 'sc_logo_with_text.png',
        "image_dark": 'sc_logo_with_text.png',
    },
    "github_url": "https://github.com/siliconcompiler/siliconcompiler",  # these are top right

    # Add light/dark mode and documentation version switcher:
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "footer_start": ["copyright", "version"]
}

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
