from typing import Optional, Union

import os.path

from siliconcompiler.tools.slang import pyslang

from siliconcompiler.tools.slang import SlangTask


class Elaborate(SlangTask):
    '''
    Elaborate verilog design files and generate a unified file.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "include_source_paths",
            "bool",
            "true/false, if true add the source file path information",
            True)

    def set_slang_includesourcepaths(self, enable: bool,
                                     step: Optional[str] = None,
                                     index: Optional[Union[int, str]] = None):
        """
        Enables or disables adding source file path information to the output.

        Args:
            enable (bool): True to include source paths, False to exclude.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "include_source_paths", enable, step=step, index=index)

    def task(self):
        return "elaborate"

    def _output_file(self):
        if self.get_fileset_file_keys("systemverilog"):
            return f"{self.design_topmodule}.sv"
        return f"{self.design_topmodule}.v"

    def setup(self):
        super().setup()

        self.add_output_file(self._output_file())

        self.add_required_key("var", "include_source_paths")

    def runtime_options(self):
        options = super().runtime_options()
        options.extend([
            "--allow-use-before-declare",
            "--ignore-unknown-modules",
            "-Weverything"
        ])
        return options

    def run(self):
        # Override default errors
        ignored = [
            pyslang.Diags.MissingTimeScale,
            pyslang.Diags.UsedBeforeDeclared,
            pyslang.Diags.UnusedParameter,
            pyslang.Diags.UnusedDefinition,
            pyslang.Diags.UnusedVariable,
            pyslang.Diags.UnusedPort,
            pyslang.Diags.UnusedButSetNet,
            pyslang.Diags.UnusedImplicitNet,
            pyslang.Diags.UnusedButSetVariable,
            pyslang.Diags.UnusedButSetPort,
            pyslang.Diags.UnusedTypedef,
            pyslang.Diags.UnusedGenvar,
            pyslang.Diags.UnusedAssertionDecl
        ]

        self._init_driver(ignored_diagnotics=ignored)
        if self._error_code:
            return self._error_code
        ok = self._compile()
        self._diagnostics()

        manager = self._compilation.sourceManager

        add_source = self.get("var", "include_source_paths")

        # Determine which definitions are actually reachable from the elaborated
        # top module. Unreachable module/interface/program definitions are
        # dropped from the output; packages, $unit-scope declarations and
        # anything that is not an instantiable definition are always kept.
        dropped = self.__unused_definitions()

        # The top module's parameter defaults are rewritten to the values it was
        # actually elaborated with (from the fileset's -G overrides). Otherwise
        # the emitted top still advertises its original defaults, so a downstream
        # tool that re-elaborates this file from the top picks a different
        # configuration than we pruned for -- referencing modules we dropped.
        overrides = self.__top_param_overrides()

        # Spliced-in nodes keep pointing at the throwaway syntax tree they were
        # parsed from, and the rewritten tree points at those; both must outlive
        # printing or pyslang reads freed memory. Hold every such tree here for
        # the duration of the write loop.
        keepalive = []

        def rewrite_defaults(node, rewriter):
            if node in overrides and node.initializer is not None:
                tree, replacement = self.__equals_value(overrides[node])
                if replacement is not None:
                    keepalive.append(tree)
                    rewriter.replace(node.initializer, replacement)
            return None

        def print_files(out, files):
            for src_file in files:
                out.write(f'//   File: {src_file}\n')

        def make_writer():
            writer = pyslang.syntax.SyntaxPrinter(manager)

            writer.setIncludeMissing(False)
            writer.setIncludeSkipped(False)
            writer.setIncludeDirectives(False)

            writer.setExpandMacros(True)
            writer.setExpandIncludes(True)
            writer.setIncludeTrivia(True)
            writer.setIncludeComments(True)
            writer.setSquashNewlines(True)

            return writer

        with open(f'outputs/{self._output_file()}', 'w') as out:
            for tree in self._compilation.getSyntaxTrees():
                # Rewriting produces a new tree whose members are positionally
                # 1:1 with the original (only parameter defaults change), so the
                # identity-based ``dropped`` check stays keyed on the original
                # nodes while the rewritten node is what gets printed.
                orig_members = list(tree.root.members)
                if overrides:
                    # Retain the rewritten tree: its member nodes read from it
                    # while printing, so it must not be collected mid-loop.
                    rewritten = pyslang.syntax.rewrite(tree, rewrite_defaults)
                    keepalive.append(rewritten)
                    printed = list(rewritten.root.members)
                else:
                    printed = orig_members

                for orig, member in zip(orig_members, printed):
                    if orig in dropped:
                        continue

                    files = []
                    if add_source:
                        files = self.__get_files(manager, orig)

                    out.write(
                        "////////////////////////////////////////////////////////////////\n")
                    out.write("// Start:\n")
                    print_files(out, files)

                    out.write(make_writer().print(member).str() + '\n')

                    out.write("// End:\n")
                    print_files(out, files)
                    out.write(
                        "////////////////////////////////////////////////////////////////\n")

        if ok:
            return 0
        else:
            return 1

    def __unused_definitions(self):
        '''
        Returns the set of definition syntax nodes (modules, interfaces,
        programs, ...) that are not reachable from the elaborated top module(s)
        and can therefore be omitted from the output.

        Packages, $unit-scope declarations and anything that is not an
        instantiable definition are never included in this set, so they are
        always retained by the caller.
        '''
        def get_syntax(symbol):
            if hasattr(symbol, "getSyntax"):
                return symbol.getSyntax()
            return getattr(symbol, "syntax", None)

        # Every instantiable definition known to the compilation.
        all_defs = set()
        for defn in self._compilation.getDefinitions():
            syntax = get_syntax(defn)
            if syntax is not None:
                all_defs.add(syntax)

        # Record the definitions actually instantiated under the top module(s).
        # ``visit`` descends through every scope -- generate blocks, interfaces
        # and deeply nested instances -- which a hand-rolled walk over
        # instance-body members would miss. It is run per top instance rather
        # than from the root: slang also elaborates other top-level modules
        # (for diagnostics) even when --top is set, and visiting the root would
        # sweep those uninstantiated modules back in.
        used = set()

        def visitor(symbol):
            if type(symbol).__name__ == "InstanceSymbol":
                syntax = get_syntax(symbol.definition)
                if syntax is not None:
                    used.add(syntax)

        for top in self._compilation.getRoot().topInstances:
            top.visit(visitor)

        return all_defs - used

    def __top_param_overrides(self):
        '''
        Maps each top-module parameter declarator (that has a default) to the
        concrete value the module was elaborated with, rendered as a
        SystemVerilog literal.

        Only overridable module parameters are considered -- localparams are
        elaboration-internal and never appear in the parameter port list.
        '''
        def get_syntax(symbol):
            if hasattr(symbol, "getSyntax"):
                return symbol.getSyntax()
            return getattr(symbol, "syntax", None)

        overrides = {}
        for top in self._compilation.getRoot().topInstances:
            definition = getattr(top, "definition", None)
            syntax = get_syntax(definition) if definition is not None else None
            header = getattr(syntax, "header", None)
            params = getattr(header, "parameters", None)
            if params is None:
                continue

            values = {}
            for param in top.body.parameters:
                if getattr(param, "isLocalParam", False):
                    continue
                values[param.name] = str(param.value)

            for declaration in params.declarations:
                if type(declaration).__name__ != "ParameterDeclarationSyntax":
                    continue
                for declarator in declaration.declarators:
                    name = declarator.name.value
                    if declarator.initializer is not None and name in values:
                        overrides[declarator] = values[name]

        return overrides

    @staticmethod
    def __equals_value(value):
        '''
        Parses ``value`` as a SystemVerilog parameter default and returns
        ``(tree, node)`` where ``node`` is the ``EqualsValueClauseSyntax``
        (``= <value>``) to splice in as a parameter default. The owning ``tree``
        is returned alongside because the node stays bound to it and the caller
        must keep it alive until printing is done. Returns ``(None, None)`` if
        ``value`` cannot be parsed.
        '''
        tree = pyslang.syntax.SyntaxTree.fromText(
            f"module __sc_p #(parameter __sc_v = {value})();endmodule")
        header = getattr(tree.root, "header", None)
        params = getattr(header, "parameters", None)
        if params is None:
            return None, None
        for declaration in params.declarations:
            if type(declaration).__name__ == "ParameterDeclarationSyntax":
                return tree, declaration.declarators[0].initializer
        return None, None

    def __get_files(self, manager, node):
        files = set()

        from queue import Queue
        nodes = Queue(maxsize=0)
        nodes.put(node)

        def proc_range(range):
            files.add(manager.getFileName(range.start))
            files.add(manager.getFileName(range.end))

        while not nodes.empty():
            node = nodes.get()
            proc_range(node.sourceRange)
            for token in node:
                if isinstance(token, pyslang.parsing.Token):
                    proc_range(token.range)
                else:
                    nodes.put(token)

        return sorted([os.path.abspath(f) for f in files if os.path.isfile(f)])
