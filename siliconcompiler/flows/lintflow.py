from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.verilator.lint import LintTask as VerilatorLintTask
from siliconcompiler.tools.slang.lint import Lint as SlangLint


class LintFlow(Flowgraph):
    '''An RTL linting flow.

    This flow is designed to check RTL source files for stylistic, semantic,
    and syntactic issues using a specified linting tool.

    Supported tools:

        * 'slang': A linter based on the Slang compiler.
        * 'verilator': A linter based on the Verilator tool.
    '''
    def __init__(self, name: Optional[str] = None, tool: str = "slang"):
        """
        Initializes the LintFlow.

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

        if tool == "all":
            self.graph(SlangLintFlow(), name="slang")
            self.graph(VerilatorLintFlow(), name="verilator")
        elif tool == "slang":
            self.graph(SlangLintFlow())
        elif tool == "verilator":
            self.graph(VerilatorLintFlow())
        else:
            raise ValueError(f'Unsupported lint tool: {tool}')

    @classmethod
    def make_docs(cls):
        return [cls(tool="all"),
                cls(tool="slang"),
                cls(tool="verilator")]


class VerilatorLintFlow(Flowgraph):
    '''A Verilator-based RTL linting flow.

    This flow is designed to check RTL source files for stylistic, semantic,
    and syntactic issues using the Verilator tool.
    '''

    def __init__(self, name: str = "verilatorlintflow"):
        """
        Initializes the VerilatorLintFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("lint", VerilatorLintTask())


class SlangLintFlow(Flowgraph):
    '''A Slang-based RTL linting flow.

    This flow is designed to check RTL source files for stylistic, semantic,
    and syntactic issues using the Slang compiler.
    '''

    def __init__(self, name: str = "slanglintflow"):
        """
        Initializes the SlangLintFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("lint", SlangLint())


##################################################
if __name__ == "__main__":
    flow = LintFlow()
    flow.write_flowgraph(f"{flow.name}.png")
