import os
import siliconcompiler
import json

def test_graph():

    chip = siliconcompiler.Chip('test')

    #RTL
    chip.pipe('rtl', [{'import' : ('surelog', 'import')},
                      {'syn' : ('yosys', 'syn')},
                      {'export' : ('nop', 'nop')},])

    #APR
    chip.pipe('apr', [{'import' : ('nop', 'import')},
                      {'floorplan' : ('openroad', 'floorplan')},
                      {'physyn' : ('openroad', 'physyn')},
                      {'place' : ('openroad', 'place')},
                      {'cts' : ('openroad', 'cts')},
                      {'route' : ('openroad', 'route')},
                      {'dfm' : ('openroad', 'dfm')},
                      {'export' : ('klayout', 'export')}])

    #SIGNOFF
    chip.node('signoff', 'import', 'nop', 'import')
    chip.node('signoff', 'extspice', 'magic', 'extspice')
    chip.node('signoff', 'drc', 'magic', 'drc')
    chip.node('signoff', 'lvs', 'netgen', 'lvs')
    chip.node('signoff', 'export', 'join', 'export')

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
