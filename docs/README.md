# SC Documentation

This directory contains the SiliconCompiler documentation, powered by
[Sphinx](https://www.sphinx-doc.org/en/master/).

Contributor process — branches, tests, linters, pull requests — lives in
[CONTRIBUTING.md](../CONTRIBUTING.md). This file covers only how the docs
themselves are put together.

## Building

```sh
pip install -e ..[docs]
sudo apt install graphviz xdot     # macOS: brew install graphviz
make html
```

Open `_build/html/index.html` to view the result, or serve the directory with
`python3 -m http.server -d _build/html` and browse to
<http://localhost:8000>. Serving is worth the extra step if you want to try the
search box: result summaries are fetched with JavaScript, which browsers block on
`file://` URLs, so search looks broken when you open the file directly.

**Warnings are errors.** `Makefile` passes `-W --keep-going` to Sphinx and Read
the Docs sets `fail_on_warning`, so a broken cross-reference or malformed
directive fails the build instead of shipping. Nitpicky mode (`-n`) is
deliberately off — it reports unresolved type names in docstrings, which is a
different problem and would bury the signal.

For PDF output, `make latexpdf`, which additionally needs:

```sh
sudo apt install latexmk texlive-latex-extra imagemagick
```

Run `make` with no target for the full list Sphinx supports.

## Structure

`index.rst` is the entry point. It leads to three top-level sections:

| Section | Directory | Contents |
|---|---|---|
| User Guide | `user_guide/` | Installation, quickstart, fundamentals, tutorials, FAQ, glossary |
| Advanced Guide | `development_guide/` | Building tools, flows, PDKs, libraries and targets; packaging; remote execution |
| References | `reference_manual/` | Schema and Python API, CLI apps, pre-defined module catalogues, appendices |

`conf.py` holds the Sphinx configuration. `_static/` holds CSS and the custom
search scorer; `_ext/` holds the Sphinx extensions that live with the docs rather
than with the package.

Most of the site is generated rather than written. The schema reference, the
pre-defined tool/flow/PDK/library/target catalogues, the CLI app reference and
the tool install matrix are all built from the source tree at build time, by
`siliconcompiler.schema.docs.schemagen` plus the extensions in `_ext/`. Editing
those pages means editing the generator or the docstrings behind them, not the
`.rst`.

`user_guide/tutorials/examples` is a symlink to the top-level `examples/`
directory, so tutorials can pull real, tested code in with `literalinclude`
instead of pasting snippets that drift out of date.

## Writing

Pages are written in
[reStructuredText](https://docutils.sourceforge.io/rst.html). A few conventions
worth following:

- **Cross-reference with `:ref:`.** Writing ``` `Text <some_label>`_ ``` looks
  right and is silently wrong: it produces a link to a relative URL rather than a
  cross-reference, and Sphinx does not warn. `tests/docs/test_rst_lint.py`
  catches it.
- **Pull code in, do not paste it.** Prefer `literalinclude` from a file under
  `examples/` so the code cannot rot independently of the page that shows it.

  Address the code by name — `:pyobject:`, or `:start-at:`/`:end-at:`/
  `:end-before:` anchored on a line that is already in the file. **`:lines:` is
  a trap**: inserting a line anywhere above the range silently shifts it, and
  the page then renders the wrong code with a clean build. There are none left
  in `docs/`; keep it that way.

  This is not hypothetical. Before they were converted, four of the ranges in
  `hardened.rst`/`uniquify.rst` had already drifted and were rendering
  half-docstrings and the wrong two lines — for long enough to be on `main`,
  with every build green.
- **Diagrams are `.dot` sources, rendered at build time.** Commit the `.dot` and
  point at it; do not commit the rendered image:

  ```rst
  .. graphviz:: _images/multi_job/together.dot
     :align: center
  ```

  `sphinx.ext.graphviz` renders it to SVG during the build, so editing a diagram
  is editing one text file — nobody has to remember to re-run `dot` and commit
  the result, and the change shows up as a readable diff. `:align:`, `:alt:`,
  `:caption:`, `:class:` and `:name:` are passed through.

  A flowgraph or dependency graph is not a hand-drawn diagram — its source is the
  Python that builds it. Render those from the example script the page already
  shows, using the `scflowgraph` and `scdepgraph` directives in `_ext/graphgen.py`:

  ```rst
  .. scdepgraph:: examples/macro_reuse/make.py
     :variable: Top()
  ```

  Trailing parentheses mean "call this"; arguments must be literals, so
  `:variable: _project("rtl.memory")` renders one particular configuration and
  the RST says which.
- **Screenshots live in `_screenshots/`, and only screenshots do.** Everything
  under `_images/` is a `.dot` source; everything under `_screenshots/` is a
  committed capture that nothing can regenerate and that therefore goes stale on
  its own. See `_screenshots/README.md` before adding one.
- **Link new pages from somewhere a reader will be.** A page reachable only
  through the toctree tends to go unread; ask what already links to it.
- **Docstrings are Google style**, rendered by the bundled
  [`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html).
  To pull in API documentation for a module:

  ```rst
  .. automodule:: siliconcompiler.<mod_name>
      :members:
  ```

  See `reference_manual/schema_api.rst` for worked examples.
