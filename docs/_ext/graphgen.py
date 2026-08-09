"""Render a flowgraph or dependency graph from an example script, at build time.

The graph pictures on the narrative pages used to be images generated once by
hand and committed. That makes them silently wrong the moment the example they
illustrate changes -- the same failure mode as pasted code, and the reason those
pages use ``literalinclude`` rather than pasted snippets.

Unlike the hand-drawn diagrams, these graphs' source is not a ``.dot`` file.
Their source is the Python that builds them, so a committed ``.dot`` would be
just as derived as the image, with the added problem that ``write_flowgraph``
emits post-layout dot (baked-in coordinates) that nobody can sensibly edit.
These directives therefore render straight from the script the page already
shows::

    .. scflowgraph:: examples/heartbeat_flowgraph.py
       :variable: flow
       :landscape:
       :align: center

    .. scdepgraph:: examples/macro_reuse/make.py
       :variable: Top()

The picture and the code excerpt above it can no longer disagree.

``:variable:`` names something the script defines. Write it with trailing
parentheses -- ``Top()``, ``_configure("rtl.memory")`` -- to have the directive
call it, which is how a class such as a :class:`Design` subclass, or a function
that assembles a project, is rendered. Arguments must be literals (they are read
with :func:`ast.literal_eval`, so no expressions and no keywords). The RST then
says exactly what was drawn.
"""

import ast
import hashlib
import importlib.util
import os
import re

from docutils.parsers.rst import directives

from sphinx.util.docutils import SphinxDirective

from siliconcompiler.schema.docs.utils import image


class ScGraph(SphinxDirective):
    """Import an object from an example script and render its graph."""

    #: Name of the ``write_*`` method to call on the resolved object.
    writer = None
    #: Subdirectory of ``_images/gen/`` the result is written to.
    subdir = None
    #: ``:variable:`` value used when the directive does not carry one.
    default_variable = None

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        "variable": directives.unchanged,
        "landscape": directives.flag,
        "align": directives.unchanged,
    }

    #: ``name`` or ``name(literal, ...)``.
    TARGET = re.compile(r"^(\w+)(?:\((.*)\))?$", re.DOTALL)

    def _parse_target(self, target):
        """Split a ``:variable:`` value into a name and the literal args to call it with.

        Returns ``(name, None)`` for a bare name, meaning "do not call".
        """
        match = self.TARGET.match(target.strip())
        if not match:
            raise self.error(f"cannot parse :variable: '{target}'")
        name, args = match.groups()
        if args is None:
            return name, None
        try:
            # A trailing comma makes the single-argument case a tuple too.
            return name, ast.literal_eval(f"({args},)") if args.strip() else ()
        except (ValueError, SyntaxError):
            raise self.error(
                f"arguments to '{name}' must be literals, got '{args}'")

    def run(self):
        _, script = self.env.relfn2path(self.arguments[0])
        script = os.path.abspath(script)

        # Rebuild the page whenever the script it renders changes.
        self.env.note_dependency(script)
        self.env.note_dependency(__file__)

        target = self.options.get("variable", self.default_variable)
        name, args = self._parse_target(target)

        # Load under a private name so importing it cannot collide with, or be
        # satisfied from, anything already in sys.modules.
        digest = hashlib.sha1(f"{script}:{target}".encode()).hexdigest()[:12]
        spec = importlib.util.spec_from_file_location(f"_scgraph_{digest}", script)
        module = importlib.util.module_from_spec(spec)

        # The scripts are run from their own directory: they are written to be
        # executed by a reader standing in that directory, and some of them read
        # or write files relative to it.
        cwd = os.getcwd()
        os.chdir(os.path.dirname(script))
        try:
            spec.loader.exec_module(module)

            if not hasattr(module, name):
                raise self.error(
                    f"{self.arguments[0]} defines no '{name}'; "
                    "set :variable: to the name of the object to render")
            obj = getattr(module, name)
            if args is not None:
                obj = obj(*args)

            if not hasattr(obj, self.writer):
                raise self.error(
                    f"'{target}' in {self.arguments[0]} has no {self.writer}()")

            outfile = os.path.join(
                self.env.app.outdir, "_images", "gen", self.subdir, f"{digest}.svg")
            os.makedirs(os.path.dirname(outfile), exist_ok=True)
            getattr(obj, self.writer)(
                outfile, landscape="landscape" in self.options)
        finally:
            os.chdir(cwd)

        return [image(outfile, center=self.options.get("align") == "center")]


class ScFlowgraph(ScGraph):
    """Render the compilation flowgraph a script builds."""

    writer = "write_flowgraph"
    subdir = "flows"
    default_variable = "flow"


class ScDepgraph(ScGraph):
    """Render the design/fileset dependency graph a script builds."""

    writer = "write_depgraph"
    subdir = "deps"
    default_variable = "project"


def setup(app):
    app.add_directive("scflowgraph", ScFlowgraph)
    app.add_directive("scdepgraph", ScDepgraph)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
