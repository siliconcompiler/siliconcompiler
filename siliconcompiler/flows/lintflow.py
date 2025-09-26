from siliconcompiler.tools.verilator import lint as verilator_lint
from siliconcompiler.tools.slang import lint as slang_lint


from siliconcompiler import Flowgraph


class LintFlow(Flowgraph):
    '''An RTL linting flow.

    This flow is designed to check RTL source files for stylistic, semantic,
    and syntactic issues using a specified linting tool.

    Supported tools:

        * 'slang': A linter based on the Slang compiler.
        * 'verilator': A linter based on the Verilator tool.
    '''
    def __init__(self, name: str = None, tool: str = "slang"):
        """
        Initializes the LintFlowgraph.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'lintflow-<tool>'.
            tool (str): The linting tool to use. Supported options are
                'slang' and 'verilator'.

        Raises:
            ValueError: If an unsupported lint tool is specified.
        """
        if name is None:
            name = f"lintflow-{tool}"
        super().__init__(name)

        if tool == "slang":
            self.node("lint", slang_lint.Lint())
        elif tool == "verilator":
            self.node("lint", verilator_lint.LintTask())
        else:
            raise ValueError(f'Unsupported lint tool: {tool}')


##################################################
if __name__ == "__main__":
    flow = LintFlow()
    flow.write_flowgraph(f"{flow.name}.png")
