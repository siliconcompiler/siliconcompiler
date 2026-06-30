'''
Elaboration flows.

Each flow in this module takes an RTL design (in one of several source
languages) and converts it into Verilog. Regardless of the input language, the
final node of every flow emits Verilog, so these flows can be used
interchangeably as a front-end for any downstream flow that consumes a Verilog
netlist (e.g. synthesis).
'''

from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.slang.elaborate import Elaborate as VerilogElaborate

from siliconcompiler.tools.bambu.convert import ConvertTask as BambuConvertTask
from siliconcompiler.tools.ghdl.convert import ConvertTask as GHDLConvertTask
from siliconcompiler.tools.sv2v.convert import ConvertTask as SV2VConvertTask
from siliconcompiler.tools.chisel.convert import ConvertTask as ChiselConvertTask


class ElaborationFlow(Flowgraph):
    '''A flow which elaborates an RTL design from its source files.

    This flow performs only the elaboration portion of the synthesis flow,
    producing an elaborated design without running synthesis or timing
    analysis. It is useful for quickly checking that a design elaborates
    cleanly.

    The flow consists of the following step:
        * **elaborate**: Elaborates the RTL design from its source files.

    The final node, **elaborate**, emits Verilog.
    '''

    def __init__(self, name: Optional[str] = None, language: str = "verilog"):
        """
        Initializes the ElaborationFlow.

        Args:
            * name (str, optional): The name of the flow. If not provided, it
                defaults to 'elaborationflow-<language>'.
            * language (str): The hardware description language of the design.
        """
        if name is None:
            name = f"elaborationflow-{language}"
        super().__init__(name)

        if language == "verilog" or language == "systemverilog":
            self.graph(SlangElaborationFlow())
        elif language == "systemverilog-sv2v":
            self.graph(SV2VElaborationFlow())
        elif language == "chisel":
            self.graph(ChiselElaborationFlow())
        elif language == "vhdl":
            self.graph(VHDLElaborationFlow())
        elif language == "hls":
            self.graph(HLSElaborationFlow())
        else:
            raise ValueError(f"Unsupported language: {language}")

    @classmethod
    def make_docs(cls):
        return [cls(language="verilog"),
                cls(language="systemverilog"),
                cls(language="systemverilog-sv2v"),
                cls(language="chisel"),
                cls(language="vhdl"),
                cls(language="hls")]


class SlangElaborationFlow(Flowgraph):
    '''
    A flow which elaborates an RTL design from its source files.

    This flow performs only the elaboration portion of the synthesis flow,
    producing an elaborated design without running synthesis or timing
    analysis. It is useful for quickly checking that a design elaborates
    cleanly.

    The flow consists of the following step:
        * **elaborate**: Elaborates the RTL design from its source files.

    The final node, **elaborate**, emits Verilog.
    '''

    def __init__(self, name: str = "slangelaborationflow"):
        """
        Initializes the SlangElaborationFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("elaborate", VerilogElaborate())


class SV2VElaborationFlow(Flowgraph):
    '''A SystemVerilog-to-Verilog elaboration flow.

    This flow is intended for designs written in SystemVerilog that may not be
    fully supported by downstream tools. It inserts a 'convert' step using SV2V
    before the standard 'elaborate' step to ensure the design is in a
    compatible Verilog format.

    The final node, **elaborate**, emits Verilog.
    '''

    def __init__(self, name: str = "sv2velaborationflow"):
        """
        Initializes the SV2VElaborationFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("elaborate", VerilogElaborate())
        self.node("convert", SV2VConvertTask())
        self.edge("elaborate", "convert")


class HLSElaborationFlow(Flowgraph):
    '''A High-Level Synthesis (HLS) elaboration flow.

    This flow supports C-based HLS by using a 'convert' step which handles the
    conversion of HLS C code to RTL using the Bambu tool.

    The final node, **convert**, emits Verilog.
    '''

    def __init__(self, name: str = "hlselaborationflow"):
        """
        Initializes the HLSElaborationFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("convert", BambuConvertTask())


class VHDLElaborationFlow(Flowgraph):
    '''A VHDL-based elaboration flow.

    This flow supports VHDL input by using a 'convert' step which uses GHDL to
    analyze and elaborate the VHDL design.

    The final node, **convert**, emits Verilog.
    '''

    def __init__(self, name: str = "vhdlelaborationflow"):
        """
        Initializes the VHDLElaborationFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("convert", GHDLConvertTask())


class ChiselElaborationFlow(Flowgraph):
    '''A Chisel-based elaboration flow.

    This flow supports designs written in the Chisel hardware construction
    language by using a 'convert' step that uses the Chisel compiler to
    generate Verilog from the Chisel source.

    The final node, **convert**, emits Verilog.
    '''

    def __init__(self, name: str = "chiselelaborationflow"):
        """
        Initializes the ChiselElaborationFlow.

        Args:
            * name (str): The name of the flow.
        """
        super().__init__(name)

        self.node("convert", ChiselConvertTask())


##################################################
if __name__ == "__main__":
    for flowcls in [SlangElaborationFlow,
                    SV2VElaborationFlow,
                    HLSElaborationFlow,
                    VHDLElaborationFlow,
                    ChiselElaborationFlow]:
        flow = flowcls()
        flow.write_flowgraph(f"{flow.name}.png")
