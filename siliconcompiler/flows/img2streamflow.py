from typing import Optional

from siliconcompiler import Flowgraph

from siliconcompiler.tools.klayout import img2stream

from siliconcompiler.flows.drcflow import DRCFlow


class Img2StreamFlow(Flowgraph):
    '''An image-to-stream flow with DRC verification.

    This flow converts an image file (PNG/JPG) to a GDSII or OASIS stream
    using KLayout, then runs a design rule check on the resulting layout.
    '''
    def __init__(self, name: Optional[str] = None, drc: Optional[str] = None):
        if name is None:
            name = f"img2streamflow-{drc}" if drc else "img2streamflow"
        super().__init__(name)

        self.node('image', img2stream.Img2StreamTask())

        if drc:
            self.graph(DRCFlow(tool=drc))
            self.edge('image', 'drc')

    @classmethod
    def make_docs(cls):
        return [
            cls(),
            cls(drc="klayout"),
            cls(drc="magic")
        ]


##################################################
if __name__ == "__main__":
    flow = Img2StreamFlow()
    flow.write_flowgraph(f"{flow.name}.png")
