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

        def print_files(out, files):
            for src_file in files:
                out.write(f'//   File: {src_file}\n')

        with open(f'outputs/{self._output_file()}', 'w') as out:
            for tree in self._compilation.getSyntaxTrees():
                files = []
                if add_source:
                    files = self.__get_files(manager, tree)

                writer = pyslang.SyntaxPrinter(manager)

                writer.setIncludeMissing(False)
                writer.setIncludeSkipped(False)
                writer.setIncludeDirectives(False)

                writer.setExpandMacros(True)
                writer.setExpandIncludes(True)
                writer.setIncludeTrivia(True)
                writer.setIncludeComments(True)
                writer.setSquashNewlines(True)

                out.write("////////////////////////////////////////////////////////////////\n")
                out.write("// Start:\n")
                print_files(out, files)

                out.write(writer.print(tree).str() + '\n')

                out.write("// End:\n")
                print_files(out, files)
                out.write("////////////////////////////////////////////////////////////////\n")

        if ok:
            return 0
        else:
            return 1

    def __get_files(self, manager, tree):
        files = set()

        from queue import Queue
        nodes = Queue(maxsize=0)
        nodes.put(tree.root)

        def proc_range(range):
            files.add(manager.getFileName(range.start))
            files.add(manager.getFileName(range.end))

        while not nodes.empty():
            node = nodes.get()
            proc_range(node.sourceRange)
            for token in node:
                if isinstance(token, pyslang.Token):
                    proc_range(token.range)
                else:
                    nodes.put(token)

        return sorted([os.path.abspath(f) for f in files if os.path.isfile(f)])
