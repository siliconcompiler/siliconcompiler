from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.sby.bmc import BMCTask
from siliconcompiler.tools.sby.prove import ProveTask
from siliconcompiler.tools.sby.cover import CoverTask


class FormalFlow(Flowgraph):
    '''A formal property verification flow.

    This flow checks the SVA assertions embedded in the RTL source
    files using SymbiYosys (sby) on top of Yosys and SMT solvers.

    Supported modes:

        * 'bmc': bounded model check of all assertions.
        * 'prove': unbounded proof via k-induction.
        * 'cover': reachability check of all cover statements.
    '''

    def __init__(self, name: Optional[str] = None, mode: str = "bmc"):
        """
        Initializes the FormalFlow.

        Args:
            name (str, optional): The name of the flow. If not provided, it
                defaults to 'formalflow-<mode>'.
            mode (str): The sby verification mode. Supported options are
                'bmc', 'prove', and 'cover'.

        Raises:
            ValueError: If an unsupported mode is specified.
        """
        if name is None:
            name = f"formalflow-{mode}"
        super().__init__(name)

        if mode == "bmc":
            task = BMCTask()
        elif mode == "prove":
            task = ProveTask()
        elif mode == "cover":
            task = CoverTask()
        else:
            raise ValueError(f'Unsupported formal mode: {mode}')

        self.node("formal", task)

    @classmethod
    def make_docs(cls):
        return [cls(mode="bmc"),
                cls(mode="prove"),
                cls(mode="cover")]


##################################################
if __name__ == "__main__":
    flow = FormalFlow()
    flow.write_flowgraph(f"{flow.name}.png")
