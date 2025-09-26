from siliconcompiler.tools.openroad import rcx_bench
from siliconcompiler.tools.openroad import rcx_extract
from siliconcompiler.tools.builtin import nop

from siliconcompiler import Flowgraph
from siliconcompiler import Task


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
    def __init__(self, extraction_task: Task = None, corners: int = 1,
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

        self.node("bench", rcx_bench.ORXBenchTask())
        for n in range(corners):
            # For each corner generate a pex step to build the reference SPEF file
            # and the extract step to use the SPEF file to build the new OpenRCX deck
            self.node('pex', extraction_task, index=n)
            self.edge('bench', 'pex', head_index=n)

            self.node('extract', rcx_extract.ORXExtractTask(), index=n)
            self.edge('pex', 'extract', head_index=n, tail_index=n)
            self.edge('bench', 'extract', head_index=n)

            if serial_extraction and n > 0:
                # For license restrictions make each pex step dependent on the previous pex step

                if n == 0:
                    prev = 'bench'
                    prev_index = 0
                else:
                    prev = 'pex'
                    prev_index = n - 1

                self.edge(prev, 'pex', head_index=n, tail_index=prev_index)

    @classmethod
    def make_docs(cls):
        from siliconcompiler.tools.builtin.nop import NOPTask
        return [GenerateOpenRCXFlow(NOPTask(), corners=3, serial_extraction=False),
                GenerateOpenRCXFlow(NOPTask(), corners=3, serial_extraction=True)]


##################################################
if __name__ == "__main__":
    flow = GenerateOpenRCXFlow(nop.NOPTask(), corners=3, serial_extraction=True)
    flow.write_flowgraph(f"{flow.name}.png", background="white")
