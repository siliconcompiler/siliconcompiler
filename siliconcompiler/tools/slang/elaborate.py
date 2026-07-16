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
                for member in tree.root.members:
                    if member in dropped:
                        continue

                    files = []
                    if add_source:
                        files = self.__get_files(manager, member)

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

        # Walk the elaborated hierarchy from the top module(s) and record the
        # definitions that are actually instantiated.
        used = set()
        seen = set()

        def visit(instance):
            body = instance.body
            if body in seen:
                return
            seen.add(body)

            defn = getattr(body, "definition", None)
            if defn is not None:
                syntax = get_syntax(defn)
                if syntax is not None:
                    used.add(syntax)

            for member in body:
                if isinstance(member, pyslang.ast.InstanceSymbol):
                    visit(member)

        for top in self._compilation.getRoot().topInstances:
            visit(top)

        return all_defs - used

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
