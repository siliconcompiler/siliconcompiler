import siliconcompiler

import importlib
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import floorplan
from siliconcompiler.tools.openroad import physyn
from siliconcompiler.tools.openroad import place
from siliconcompiler.tools.openroad import cts
from siliconcompiler.tools.openroad import route
from siliconcompiler.tools.openroad import dfm
from siliconcompiler.tools.klayout import export

from siliconcompiler.tools.magic import extspice
from siliconcompiler.tools.magic import drc
from siliconcompiler.tools.netgen import lvs

def test_graph():

    chip = siliconcompiler.Chip('test')

    #RTL
    chip.pipe('rtl', [{'import' : importlib.import_module('siliconcompiler.tools.surelog.import')},
                      {'syn' : syn_asic},
                      {'export' : 'builtin.nop'},])

    #APR
    chip.pipe('apr', [{'import' : 'builtin.import'},
                      {'floorplan' : floorplan},
                      {'physyn' : physyn},
                      {'place' : place},
                      {'cts' : cts},
                      {'route' : route},
                      {'dfm' : dfm},
                      {'export' : export}])

    #SIGNOFF
    chip.node('signoff', 'import', 'builtin.import')
    chip.node('signoff', 'extspice', extspice)
    chip.node('signoff', 'drc', drc)
    chip.node('signoff', 'lvs', lvs)
    chip.node('signoff', 'export', 'bulitin.join')

    chip.edge('signoff', 'import', 'drc')
    chip.edge('signoff', 'import', 'extspice')
    chip.edge('signoff', 'extspice', 'lvs')
    chip.edge('signoff', 'lvs', 'export')
    chip.edge('signoff', 'drc', 'export')

    #TOP
    chip.graph("top","rtl", name="rtl")
    chip.graph("top","apr", name="apr")
    chip.graph("top","signoff", name="dv")
    chip.edge("top", "rtl", "apr")
    chip.edge("top", "apr", "dv")

    chip.write_flowgraph("top.png", flow="top")

#########################
if __name__ == "__main__":
    test_graph()
