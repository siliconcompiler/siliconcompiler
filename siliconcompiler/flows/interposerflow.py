from siliconcompiler import FlowgraphSchema

from siliconcompiler.tools.openroad import rdlroute
from siliconcompiler.tools.klayout import export


class InterposerFlow(FlowgraphSchema):
    '''
    A flow to perform RDL routing and generate a GDS
    '''
    def __init__(self):
        super().__init__("interposerflow")

        self.node("rdlroute", rdlroute.RDLRouteTask())
        self.node("write_gds", export.ExportTask())
        self.edge('rdlroute', 'write_gds')


##################################################
if __name__ == "__main__":
    flow = InterposerFlow()
    flow.write_flowgraph(f"{flow.name}.png")
