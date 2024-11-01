from siliconcompiler import Flow

from siliconcompiler.tools.klayout import drc


def setup():
    '''
    Perform a DRC run on an input GDS
    '''
    flow = Flow('drcflow')
    flow.node('drcflow', 'drc', drc)

    return flow
