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
import os
import sys
from datetime import date
import inspect
import importlib

sc_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, sc_root)
import siliconcompiler  # noqa E402
sys.path.append(os.path.join(sc_root, 'docs', '_ext'))

from siliconcompiler import __version__ as sc_version  # noqa E402


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
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.imgconverter',
    'sphinx.ext.autosummary',
    "sphinx.ext.linkcode",
    'siliconcompiler.sphinx_ext.dynamicgen',
    'siliconcompiler.sphinx_ext.schemagen',
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

suppress_warnings = ['autosectionlabel.*']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

html_theme_options = {
    "collapse_navigation": True,
    "show_toc_level": 2,   # this automatically displays two levels
    "logo": {
        "image_light": '_images/sc_logo_with_text.png',
        "image_dark": '_images/sc_logo_with_text.png',
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

linkcheck_timeout = 5

# Modified from: https://github.com/readthedocs/sphinx-autoapi/issues/202#issuecomment-1048104024
code_url = f"{html_theme_options['github_url']}/blob/v{sc_version}"


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
    file = os.path.relpath(file, sc_root)
    if not file.startswith("siliconcompiler"):
        # e.g. object is a typing.NewType
        return None
    start, end = lines[1], lines[1] + len(lines[0]) - 1

    return f"{code_url}/{file}#L{start}-L{end}"
