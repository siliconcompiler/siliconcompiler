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

sys.path.insert(0, os.path.abspath('../siliconcompiler'))
import siliconcompiler  # noqa E402
sys.path.append(os.path.abspath('./_ext'))


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
    'siliconcompiler.sphinx_ext.dynamicgen',
    'schemagen',
    'clientservergen',
    'requirements',
    'installgen'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

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
    "show_toc_level": 3,   # this automatically displays three levels
    "logo": {
        "image_light": 'sc_logo_with_text.png',
        "image_dark": 'sc_logo_with_text.png',
    },
    "github_url": "https://github.com/siliconcompiler/siliconcompiler",  # these are top right

    # Add light/dark mode and documentation version switcher:
    "navbar_end": ["theme-switcher", "navbar-icon-links"]
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

# -- Options for autodoc -----------------------------------------------------
autodoc_mock_imports = ['siliconcompiler.leflib._leflib']
