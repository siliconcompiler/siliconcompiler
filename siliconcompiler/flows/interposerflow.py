from siliconcompiler import Flowgraph

from siliconcompiler.tools.openroad import rdlroute
from siliconcompiler.tools.klayout import export


class InterposerFlow(Flowgraph):
    '''A flow to perform Redistribution Layer (RDL) routing and generate a GDS.

    This flow is designed for creating interposers or other simple routing
    layers. It uses OpenROAD for RDL routing and KLayout to export the
    final layout to a GDSII file.

    The flow consists of the following steps:

        * **rdlroute**: Performs RDL routing on the input design.
        * **write_gds**: Exports the routed design to a GDSII file.
    '''
    def __init__(self):
        """
        Initializes the InterposerFlow.
        """
        super().__init__("interposerflow")

        self.node("rdlroute", rdlroute.RDLRouteTask())
        self.node("write_gds", export.ExportTask())
        self.edge('rdlroute', 'write_gds')


##################################################
if __name__ == "__main__":
    flow = InterposerFlow()
    flow.write_flowgraph(f"{flow.name}.png")
