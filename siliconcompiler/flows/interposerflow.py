from siliconcompiler import Flow

from siliconcompiler.tools.openroad import rdlroute
from siliconcompiler.tools.klayout import export


def setup():
    '''
    A flow to perform RDL routing and generate a GDS
    '''
    flow = Flow('interposerflow')
    flow.node('interposerflow', 'rdlroute', rdlroute)
    flow.node('interposerflow', 'write_gds', export)

    flow.edge('interposerflow', 'rdlroute', 'write_gds')

    return flow
