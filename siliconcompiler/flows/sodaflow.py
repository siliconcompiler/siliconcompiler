'''
SODA front-end flows.

`SODA Synthesizer <https://github.com/pnnl/soda-opt>`_ compiles a
high-level machine learning model down to accelerator RTL. Its front end,
:ref:`soda-opt <tool-soda>`, works in MLIR: a model exported through TOSA is
lowered to linalg, a kernel is outlined from it and optimized for high-level
synthesis, and the result is handed to an HLS tool -- :ref:`Bambu <tool-bambu>`
-- which emits the Verilog.

This module provides that path as a set of SiliconCompiler elaboration flows, so
the Verilog it produces continues into the ordinary synthesis and
place-and-route flows rather than into a separate backend. Any flow that takes a
``frontend`` -- :class:`~siliconcompiler.flows.elaborationflow.ElaborationFlow`,
:class:`~siliconcompiler.flows.synflow.SynthesisFlow` and
:class:`~siliconcompiler.flows.asicflow.ASICFlow` -- can be handed one of these,
which is how a model reaches GDSII in a single job. Upstream, the equivalent of
everything downstream of Bambu is a generated ``config.mk`` handed to
OpenROAD-flow-scripts.

soda-opt offers three ways to lower the outlined kernel, and each is a flow of
its own rather than an argument: :class:`SODABaselineElaborationFlow`,
:class:`SODAOptimizedElaborationFlow` and
:class:`SODATransformedElaborationFlow`.

The flows' input is a bufferized-or-not TOSA module. Their output is Verilog for
the outlined kernel, whose name -- and therefore the design's topmodule -- is
the entry function suffixed with ``_kernel``: a model whose entry point is
``forward`` yields ``forward_kernel``.

.. important::

   The final node needs a Bambu built against clang 16. LLVM 19 emits opaque
   pointers unconditionally, and an older Bambu front end rejects the IR.
   See the install note in :ref:`the SODA tutorial <soda_tutorial>`.
'''

from siliconcompiler import Flowgraph, Task

from siliconcompiler.tools.mlir.opt import TosaToLinalgTask, BufferizeTask
from siliconcompiler.tools.mlir.translate import TranslateTask
from siliconcompiler.tools.mlir.compile import RuntimeTask
from siliconcompiler.tools.mlir.link import LinkTask
from siliconcompiler.tools.soda.opt import BaselineTask, OptimizedTask, TransformedTask
from siliconcompiler.tools.bambu.convert import ConvertTask as BambuConvertTask


class SODAElaborationFlow(Flowgraph):
    '''An MLIR-to-Verilog elaboration flow built on the SODA Synthesizer.

    The flow consists of the following steps:

        * **tosa2linalg**: Lowers the TOSA module to linalg on tensors.
        * **bufferize**: Puts that linalg on buffers, turning the function's
          results into out-parameters.
        * **soda**: Outlines the kernel, optimizes it for high-level synthesis
          and lowers it to the LLVM dialect.
        * **translate**: Translates the LLVM dialect into LLVM IR.
        * **runtime**: Compiles the MLIR runtime helpers to LLVM IR. This has no
          design input, so it is a second entry node and runs alongside the rest.
        * **link**: Merges those helpers into the kernel, if it calls them.
        * **convert**: Synthesizes the LLVM IR into Verilog with Bambu.

    The final node, **convert**, emits Verilog.

    How the **soda** node lowers the outlined kernel is the one thing the three
    SODA strategies differ in, so it is left to the subclasses:
    :class:`SODABaselineElaborationFlow`,
    :class:`SODAOptimizedElaborationFlow` and
    :class:`SODATransformedElaborationFlow`.

    This class is the part they share; it is not a flow on its own.
    '''

    ###############################################################
    # Definition, overridden by each strategy
    ###############################################################
    def _strategy(self) -> Task:
        """
        Task that lowers the outlined kernel to the LLVM dialect.
        """
        raise NotImplementedError("must be implemented by the strategy specific flow")

    def __init__(self, name: str):
        """Initializes the flow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("tosa2linalg", TosaToLinalgTask())
        self.node("bufferize", BufferizeTask())
        self.node("soda", self._strategy())
        self.node("translate", TranslateTask())
        self.node("runtime", RuntimeTask())
        self.node("link", LinkTask())
        self.node("convert", BambuConvertTask())

        self.edge("tosa2linalg", "bufferize")
        self.edge("bufferize", "soda")
        self.edge("soda", "translate")
        self.edge("translate", "link")
        self.edge("runtime", "link")
        self.edge("link", "convert")
        # soda-opt writes the kernel's C testbench alongside the kernel itself.
        # bambu needs it for --generate-tb, and it comes from soda rather than
        # from link, which carries only the IR.
        self.edge("soda", "convert")


class SODABaselineElaborationFlow(SODAElaborationFlow):
    '''The SODA front end with no HLS-oriented optimization.

    The outlined kernel goes straight from linalg to the LLVM dialect, so the
    resulting RTL shows what the HLS tool makes of code nobody prepared for it.
    It is the reference the other two flows are measured against.
    '''

    def __init__(self, name: str = "sodabaselineelaborationflow"):
        """Initializes the flow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

    def _strategy(self) -> Task:
        """Task that lowers the outlined kernel to the LLVM dialect."""
        return BaselineTask()


class SODAOptimizedElaborationFlow(SODAElaborationFlow):
    '''The SODA front end with soda-opt's optimization pipeline for Bambu.

    Before lowering, the outlined kernel is tiled, given local buffers, unrolled
    and scalar-replaced, which is where most of the area and latency difference
    against the baseline comes from. Every stage of that pipeline is a setter on
    :class:`~siliconcompiler.tools.soda.opt.OptimizedTask`, so a design can be
    swept over it without touching the flow.
    '''

    def __init__(self, name: str = "sodaoptimizedelaborationflow"):
        """Initializes the flow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

    def _strategy(self) -> Task:
        """Task that lowers the outlined kernel to the LLVM dialect."""
        return OptimizedTask()


class SODATransformedElaborationFlow(SODAElaborationFlow):
    '''The SODA front end driven by a transform dialect schedule.

    Instead of the fixed optimization pipeline, the outlined kernel is rewritten
    by a schedule written in MLIR's transform dialect, which the interpreter
    applies before the schedule is erased and the kernel is lowered. It is how a
    design expresses an optimization strategy the pipeline's knobs cannot.

    The schedule is required, and is set on the task rather than on the flow::

        TransformedTask.find_task(project).set_soda_schedule("transform.mlir")
    '''

    def __init__(self, name: str = "sodatransformedelaborationflow"):
        """Initializes the flow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

    def _strategy(self) -> Task:
        """Task that lowers the outlined kernel to the LLVM dialect."""
        return TransformedTask()


#: The optimization strategies soda-opt offers, and the flow that implements each.
#:
#: A caller that takes a strategy by name -- a command line, a generated script,
#: :class:`~siliconcompiler.flows.asicflow.SODAASICFlow` -- looks the flow up
#: here rather than building a flow name out of the string.
SODA_STRATEGIES = {
    "baseline": SODABaselineElaborationFlow,
    "optimized": SODAOptimizedElaborationFlow,
    "transformed": SODATransformedElaborationFlow,
}


##################################################
if __name__ == "__main__":
    for flowcls in [SODABaselineElaborationFlow,
                    SODAOptimizedElaborationFlow,
                    SODATransformedElaborationFlow]:
        flow = flowcls()
        flow.write_flowgraph(f"{flow.name}.png")
