import os
import siliconcompiler
import json

def test_graph():

    chip = siliconcompiler.Chip('test')

    #RTL
    chip.pipe('rtl', [{'import' : 'surelog'},
                      {'syn' : 'yosys'},
                      {'export' : 'nop'},])

    #APR
    chip.pipe('apr', [{'import' : 'nop'},
                      {'floorplan' : 'openroad'},
                      {'physyn' : 'openroad'},
                      {'place' : 'openroad'},
                      {'cts' : 'openroad'},
                      {'route' : 'openroad'},
                      {'dfm' : 'openroad'},
                      {'export' : 'klayout'}])

    #SIGNOFF
    chip.node('signoff', 'import', 'nop')
    chip.node('signoff', 'extspice', 'magic')
    chip.node('signoff', 'drc', 'magic')
    chip.node('signoff', 'lvs', 'netgen')
    chip.node('signoff', 'export', 'join')

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
