from siliconcompiler.tools.openroad import rcx_bench
from siliconcompiler.tools.openroad import rcx_extract
from siliconcompiler.tools.builtin import nop

from siliconcompiler import FlowgraphSchema, TaskSchema


class GenerateOpenRCXFlow(FlowgraphSchema):
    '''
    Flow to generate the OpenRCX decks needed by OpenROAD to do parasitic
    extraction.
    '''
    def __init__(self, extraction_task: TaskSchema = None, corners: int = 1, serial_extraction: bool = False):
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


##################################################
if __name__ == "__main__":
    flow = GenerateOpenRCXFlow(nop.NOPTask(), corners=3, serial_extraction=True)
    flow.write_flowgraph(f"{flow.name}.png", background="white")
