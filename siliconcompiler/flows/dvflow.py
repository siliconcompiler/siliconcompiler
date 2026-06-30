from siliconcompiler.tools.icarus import compile as icarus_compile
from siliconcompiler.tools.icarus import cocotb_exec as icarus_cocotb
from siliconcompiler.tools.verilator import compile as verilator_compile
from siliconcompiler.tools.verilator import cocotb_compile as verilator_cocotb_compile
from siliconcompiler.tools.verilator import cocotb_exec as verilator_cocotb
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
        * 'icarus-cocotb': Compiles with Icarus and runs cocotb Python testbenches.
        * 'verilator': Compiles and simulates with Verilator.
        * 'verilator-cocotb': Compiles with Verilator and runs cocotb Python testbenches.
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
            self.graph(IcarusDVFlow(np=np))
        elif tool == "icarus-cocotb":
            self.graph(IcarusCocotbDVFlow(np=np))
        elif tool == "verilator":
            self.graph(VerilatorDVFlow(np=np))
        elif tool == "verilator-cocotb":
            self.graph(VerilatorCocotbDVFlow(np=np))
        elif tool == "xyce":
            self.graph(XyceDVFlow(np=np))
        elif tool == "xdm-xyce":
            self.graph(XDMXyceDVFlow(np=np))
        else:
            raise ValueError(f'{tool} is not a supported tool')

    @classmethod
    def make_docs(cls):
        return [cls(tool="icarus", np=3),
                cls(tool="icarus-cocotb", np=3),
                cls(tool="verilator", np=3),
                cls(tool="verilator-cocotb", np=3),
                cls(tool="xyce", np=3),
                cls(tool="xdm-xyce", np=3)]


class IcarusDVFlow(Flowgraph):
    '''A DV flow using the Icarus Verilog simulator.'''
    def __init__(self, name: str = "icarusdvflow", np: int = 1):
        super().__init__(name)

        self.node("compile", icarus_compile.CompileTask())
        sim_task = exec_input.ExecInputTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            self.edge("compile", "simulate", head_index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


class IcarusCocotbDVFlow(Flowgraph):
    '''A DV flow using the Icarus Verilog simulator with cocotb testbenches.'''
    def __init__(self, name: str = "icaruscocotbdvflow", np: int = 1):
        super().__init__(name)

        self.node("compile", icarus_compile.CompileTask())
        sim_task = icarus_cocotb.CocotbExecTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            self.edge("compile", "simulate", head_index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


class VerilatorDVFlow(Flowgraph):
    '''A DV flow using the Verilator simulator.'''
    def __init__(self, name: str = "verilatordvflow", np: int = 1):
        super().__init__(name)

        self.node("compile", verilator_compile.CompileTask())
        sim_task = exec_input.ExecInputTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            self.edge("compile", "simulate", head_index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


class VerilatorCocotbDVFlow(Flowgraph):
    '''A DV flow using the Verilator simulator with cocotb testbenches.'''
    def __init__(self, name: str = "verilatorcocotbdvflow", np: int = 1):
        super().__init__(name)

        self.node("compile", verilator_cocotb_compile.CocotbCompileTask())
        sim_task = verilator_cocotb.CocotbExecTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            self.edge("compile", "simulate", head_index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


class XyceDVFlow(Flowgraph):
    '''A DV flow using the Xyce circuit simulator.'''
    def __init__(self, name: str = "xycedvflow", np: int = 1):
        super().__init__(name)

        sim_task = xyce_simulate.SimulateTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


class XDMXyceDVFlow(Flowgraph):
    '''A DV flow using the Xyce circuit simulator with XDM conversion.'''
    def __init__(self, name: str = "xdmxycedvflow", np: int = 1):
        super().__init__(name)

        self.node("compile", xdm_convert.ConvertTask())
        sim_task = xyce_simulate.SimulateTask()

        for n in range(np):
            self.node("simulate", sim_task, index=n)
            self.edge("compile", "simulate", head_index=n)

    @classmethod
    def make_docs(cls):
        return cls(np=3)


##################################################
if __name__ == "__main__":
    for tool in ["icarus", "icarus-cocotb", "verilator", "verilator-cocotb", "xyce", "xdm-xyce"]:
        flow = DVFlow(tool=tool, np=3)
        flow.write_flowgraph(f"{flow.name}.png")
