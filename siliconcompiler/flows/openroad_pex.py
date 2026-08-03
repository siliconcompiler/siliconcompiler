from typing import Optional

from siliconcompiler import Flowgraph
from siliconcompiler import Task

from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler.tools.openroad.pex import ORXBenchTask, ORXExtractTask
from siliconcompiler.tools.openroad.pex import PEXBenchTask, PEXBenchExtractTask
from siliconcompiler.tools.openroad.pex import CalibratePEXTask
from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin.wait import Wait


class GenerateOpenRCXFlow(Flowgraph):
    '''A flow to generate OpenRCX parasitic extraction decks for OpenROAD.

    This flow automates the process of characterizing a parasitic extraction
    tool to generate the necessary configuration files (RCX decks) for
    OpenROAD's built-in OpenRCX engine. It works by comparing the output of a
    third-party "golden" extraction tool against OpenRCX's results and
    calibrating OpenRCX accordingly.

    The flow consists of the following main steps for each specified corner:

        1. **bench**: A benchmark design with simple structures is created.
        2. **pex**: A user-provided third-party PEX tool is run on the benchmark
                    to generate a "golden" SPEF file.
        3. **extract**: The golden SPEF is used to generate a calibrated OpenRCX
                        deck.
    '''
    def __init__(self, extraction_task: Optional[Task] = None, corners: int = 1,
                 serial_extraction: bool = False):
        """
        Initializes the GenerateOpenRCXFlow.

        Args:
            * extraction_task (Task): The SiliconCompiler task schema for the
                third-party PEX tool that will be used to generate the golden
                SPEF files. This is a required parameter.
            * corners (int): The number of process corners to generate RCX decks
                for. A separate 'pex' and 'extract' step will be created for
                each corner.
            * serial_extraction (bool): If True, forces the 'pex' steps for each
                corner to run sequentially rather than in parallel. This can be
                useful when the PEX tool has license limitations that prevent
                multiple concurrent runs.

        Raises:
            ValueError: If `extraction_task` is not provided.
        """
        super().__init__("generate_rcx")

        if extraction_task is None:
            raise ValueError("extraction_task is required")

        self.node("bench", ORXBenchTask())
        for n in range(corners):
            # For each corner generate a pex step to build the reference SPEF file
            # and the extract step to use the SPEF file to build the new OpenRCX deck
            self.node('pex', extraction_task, index=n)
            self.edge('bench', 'pex', head_index=n)

            self.node('extract', ORXExtractTask(), index=n)
            self.edge('pex', 'extract', head_index=n, tail_index=n)
            self.edge('bench', 'extract', head_index=n)

        if serial_extraction:
            # For license restrictions, serialize the pex steps so they run one at
            # a time. Wait tasks impose a scheduling barrier without creating a
            # data dependency between the pex steps. This serializes every node
            # using the extraction tool, which assumes the third-party PEX tool is
            # distinct from the openroad tool used by bench/extract.
            Wait.serialize_tool_tasks(self, extraction_task.tool())

    @classmethod
    def make_docs(cls):
        from siliconcompiler.tools.builtin.nop import NOPTask
        return [cls(NOPTask(), corners=3, serial_extraction=False),
                cls(NOPTask(), corners=3, serial_extraction=True)]


class GeneratePEXEstimateFlow(Flowgraph):
    '''A flow to derive the initial per-layer parasitic estimate model for a PDK.

    OpenROAD estimates pre-route parasitics from a per-layer R/C model (the PDK
    ``rclayer`` values seeded into ``set_layer_rc``). This flow generates those
    initial values directly from the PDK's OpenRCX deck, so a PDK does not need
    hand-tuned estimate values:

        1. **bench**: ``bench_wires`` builds synthetic wire patterns from the
           tech LEF and writes a pattern DEF.
        2. **extract**: the patterns are extracted with the OpenRCX deck and the
           per-segment parasitics are walked into per-layer resistance and
           capacitance.

    The output feeds :meth:`.OpenROADPDK.add_openroad_rclayer`. A design survey
    (see the ``pex_calibration`` example) then refines the estimate with
    :meth:`.OpenROADPDK.add_openroad_rccorrection`. Needs only the PDK (tech LEF
    + OpenRCX deck) - no design.
    '''
    def __init__(self, name: str = "generate_pex_estimate"):
        """Initializes the GeneratePEXEstimateFlow.

        Args:
            * name (str): The name of the flow.

        The ``bench`` node benches every routing layer in the tech, and the
        ``extract`` node derives the model for every PEX corner the PDK ships an
        OpenRCX deck for - not just the corners a target happens to wire into a
        timing scenario, since the bench needs no timing scenario at all.
        """
        super().__init__(name)

        self.node("bench", PEXBenchTask())
        self.node("extract", PEXBenchExtractTask())
        self.edge("bench", "extract")


class PEXCalibrateFlow(Flowgraph):
    '''ASIC flow that calibrates the pre-route parasitic estimate against a
    golden OpenRCX extraction.

    This takes a design from RTL through routing using the core steps of the
    :class:`.ASICFlow` (synthesis, floorplan, place, cts, route, dfm) and then,
    instead of the final view/GDS write, runs a ``calibrate`` node on the routed
    database. For each PEX corner that node compares OpenROAD's pre-route
    ``estimate_parasitics`` output against an OpenRCX ``extract_parasitics``
    golden reference. The write steps are dropped because calibration only needs
    the routed database, and they would only add runtime and tool requirements
    (SPEF/Liberty export, KLayout GDS).

    The per-layer sums the calibrate node emits are the inputs used to calibrate
    :meth:`.OpenROADPDK.add_openroad_rccorrection`; the PEX calibration utility
    (``examples/pex_calibration``) iterates this flow over a set of designs and
    pools the results into per-layer correction factors.
    '''
    def __init__(self, name: str = "pex_calibrate", language: str = "verilog"):
        """Initializes the PEXCalibrateFlow.

        Args:
            * name (str): The name of the flow.
            * language (str): The hardware description language of the design.
        """
        super().__init__(name)

        # Import the full ASIC flow, then keep only the core RTL->routed steps.
        self.graph(ASICFlow(language=language))

        # The routed database is the node that fed write.views; capture it
        # before removing the write steps.
        routed_node = self.get_graph_node("write.views", "0").get_input()[0][0]
        self.remove_node("write.views")
        self.remove_node("write.gds")

        # Calibrate on the routed database. The estimate honors whatever
        # rccorrection the PDK carries (none when deriving, the derived factors
        # when scoring), so no flow-level flag is needed.
        self.node("calibrate", CalibratePEXTask())
        self.edge(routed_node, "calibrate")


##################################################
if __name__ == "__main__":
    flow = GenerateOpenRCXFlow(nop.NOPTask(), corners=3, serial_extraction=True)
    flow.write_flowgraph(f"{flow.name}.png", background="white")
