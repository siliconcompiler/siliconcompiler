"""Render a :class:`Flowgraph` defined in an example script, at build time.

The flowgraph pictures on the narrative pages used to be SVGs generated once by
hand and committed. That makes them silently wrong the moment the example they
illustrate changes -- the same failure mode as pasted code, and the reason those
pages use ``literalinclude`` rather than pasted snippets.

Unlike the hand-drawn diagrams, a flowgraph's source is not a ``.dot`` file. Its
source is the Python that builds it, so a committed ``.dot`` would be just as
derived as the image, with the added problem that ``write_flowgraph`` emits
post-layout dot (baked-in coordinates) that nobody can sensibly edit. This
directive therefore renders straight from the script that the page already
shows::

    .. scflowgraph:: examples/heartbeat_flowgraph.py
       :variable: flow
       :landscape:
       :align: center

The picture and the code excerpt above it can no longer disagree.
"""

import hashlib
import importlib.util
import os

from docutils.parsers.rst import directives

from sphinx.util.docutils import SphinxDirective

from siliconcompiler.schema.docs.utils import image


class ScFlowgraph(SphinxDirective):
    """Import a flow from an example script and render it into the build."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        "variable": directives.unchanged,
        "landscape": directives.flag,
        "align": directives.unchanged,
    }

    def run(self):
        _, script = self.env.relfn2path(self.arguments[0])
        script = os.path.abspath(script)

        # Rebuild the page whenever the script it renders changes.
        self.env.note_dependency(script)
        self.env.note_dependency(__file__)

        variable = self.options.get("variable", "flow")

        # Load under a private name so importing it cannot collide with, or be
        # satisfied from, anything already in sys.modules.
        digest = hashlib.sha1(script.encode()).hexdigest()[:12]
        spec = importlib.util.spec_from_file_location(f"_scflowgraph_{digest}", script)
        module = importlib.util.module_from_spec(spec)

        # The scripts are run from their own directory: they are written to be
        # executed by a reader standing in that directory, and some of them write
        # files as a side effect.
        cwd = os.getcwd()
        os.chdir(os.path.dirname(script))
        try:
            spec.loader.exec_module(module)
        finally:
            os.chdir(cwd)

        if not hasattr(module, variable):
            raise self.error(
                f"{self.arguments[0]} defines no '{variable}'; "
                "set :variable: to the name of the Flowgraph")
        flow = getattr(module, variable)

        outfile = os.path.join(
            self.env.app.outdir, "_images", "gen", "flows", f"{digest}.svg")
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        flow.write_flowgraph(outfile, landscape="landscape" in self.options)

        return [image(outfile, center=self.options.get("align") == "center")]


def setup(app):
    app.add_directive("scflowgraph", ScFlowgraph)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
