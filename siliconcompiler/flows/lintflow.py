from siliconcompiler.tools.verilator import lint as verilator_lint
from siliconcompiler.tools.slang import lint as slang_lint


from siliconcompiler import FlowgraphSchema


class LintFlowgraph(FlowgraphSchema):
    '''
    An RTL linting flow.
    '''
    def __init__(self, name: str = None, tool: str = "slang"):
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
    flow = LintFlowgraph()
    flow.write_flowgraph(f"{flow.name}.png")
