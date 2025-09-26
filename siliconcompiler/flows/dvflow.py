from siliconcompiler.tools.icarus import compile as icarus_compile
from siliconcompiler.tools.verilator import compile as verilator_compile
from siliconcompiler.tools.execute import exec_input
from siliconcompiler.tools.xyce import simulate as xyce_simulate
from siliconcompiler.tools.xdm import convert as xdm_convert


from siliconcompiler import Flowgraph


class DVFlow(Flowgraph):
    '''
    A configurable constrained random stimulus DV flow.

    The verification pipeline includes the following steps:

        * **compile**: RTL sources are compiled into an intermediate format.
        * **sim**: The compiled design is simulated with a generated testbench.

    The dvflow can be parametrized using the 'np' parameter. Setting 'np' > 1
    results in multiple independent verification pipelines being launched in
    parallel.

    Supported tools are:

        * 'icarus': Compiles and simulates with the Icarus Verilog simulator.
        * 'verilator': Compiles and simulates with Verilator.
        * 'xyce': Simulates a netlist with the Xyce circuit simulator.
        * 'xdm-xyce': Converts a design to a Xyce-compatible format and simulates.
    '''
    def __init__(self, name: str = None, tool: str = "icarus", np: int = 1):
        """
        Initializes the DVFlow with a specified tool and parallelism.

        Args:
            * name (str, optional): The name of the flow. If not provided, it
                defaults to 'dvflow-<tool>'.
            * tool (str): The simulation tool to use. Supported options are
                'icarus', 'verilator', 'xyce', and 'xdm-xyce'.
            * np (int): The number of parallel simulation jobs to launch.

        Raises:
            ValueError: If an unsupported tool is specified.
        """
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
