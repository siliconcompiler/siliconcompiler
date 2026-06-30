from siliconcompiler import Flowgraph

from siliconcompiler.tools.klayout import img2stream

from siliconcompiler.flows.drcflow import KlayoutDRCFlow


class Img2StreamFlow(Flowgraph):
    '''An image-to-stream flow with DRC verification.

    This flow converts an image file (PNG/JPG) to a GDSII or OASIS stream
    using KLayout, then runs a design rule check on the resulting layout.
    '''
    def __init__(self, name: str = "img2streamflow", run_drc: bool = True):
        super().__init__(name)

        self.node('image', img2stream.Img2StreamTask())

        if run_drc:
            self.graph(KlayoutDRCFlow())
            self.edge('image', 'drc')


##################################################
if __name__ == "__main__":
    flow = Img2StreamFlow()
    flow.write_flowgraph(f"{flow.name}.png")
