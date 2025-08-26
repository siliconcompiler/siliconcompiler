import siliconcompiler

from siliconcompiler.tools.icarus import compile as icarus_compile
from siliconcompiler.tools.verilator import compile as verilator_compile
from siliconcompiler.tools.execute import exec_input
from siliconcompiler.tools.xyce import simulate as xyce_simulate
from siliconcompiler.tools.xdm import convert as xdm_convert


from siliconcompiler import FlowgraphSchema


class DVFlow(FlowgraphSchema):
    '''
    A configurable constrained random stimulus DV flow.

    The verification pipeline includes the following steps:

    * **compile**: RTL sources are compiled into object form (once)
    * **sim**: Compiled RTL is exercised using generated test

    The dvflow can be parametrized using a single 'np' parameter.
    Setting 'np' > 1 results in multiple independent verification
    pipelines to be launched.

    Supported tools are:

    * icarus
    * verilator
    * xyce
    * xdm-xyce

    This flow is a WIP
    '''
    def __init__(self, name: str = None, tool: str = "icarus", np: int = 1):
        if name is None:
            name = f"dvflow-{tool}"
        super().__init__(name)

        if tool == "icarus":
            self.node("compile", icarus_compile.CompileTask())
            sim_task = exec_input.ExecInputTask()
            com_name = "compile"
        elif tool == "verilator":
            self.node("compile", verilator_compile.CompileTask())
            sim_task = exec_input.ExecInputTask()
            com_name = "compile"
        elif tool == "xyce":
            sim_task = xyce_simulate.SimulateTask()
            com_name = None
        elif tool == "xdm-xyce":
            self.node("compile", xdm_convert.ConvertTask())
            sim_task = xyce_simulate.SimulateTask()
            com_name = "compile"
        else:
            raise ValueError(f'{tool} is not a supported tool')

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            if com_name:
                self.edge(com_name, "simulate", head_index=n)


##################################################
if __name__ == "__main__":
    flow = DVFlow(np=3)
    flow.write_flowgraph(f"{flow.name}.png")
