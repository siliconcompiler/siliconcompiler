import siliconcompiler

def test_graph():

    chip = siliconcompiler.Chip('test')

    #RTL
    chip.pipe('rtl', [{'import' : ('surelog', 'parse')},
                      {'syn' : ('yosys', 'syn')},
                      {'export' : ('builtin', 'nop')},])

    #APR
    chip.pipe('apr', [{'import' : ('builtin', 'nop')},
                      {'floorplan' : ('openroad', 'floorplan')},
                      {'physyn' : ('openroad', 'physyn')},
                      {'place' : ('openroad', 'place')},
                      {'cts' : ('openroad', 'cts')},
                      {'route' : ('openroad', 'route')},
                      {'dfm' : ('openroad', 'dfm')},
                      {'export' : ('klayout', 'export')}])

    #SIGNOFF
    chip.node('signoff', 'import', 'builtin', 'nop')
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
    chip.graph("top", "rtl", name="rtl")
    chip.graph("top", "apr", name="apr")
    chip.graph("top", "signoff", name="dv")
    chip.edge("top", "rtl.export", "apr.import")
    chip.edge("top", "apr.export", "dv.import")

    chip.write_flowgraph("top.png", flow="top")

def test_graph_entry():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=0)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=1)
    chip.node(flow, 'domin', 'builtin', 'minimum')
    chip.node(flow, 'postmin', 'fake_in', 'postmin')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    assert chip._get_flowgraph_entry_nodes() == [('premin', '0'), ('premin', '1')]

def test_graph_exit():

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    assert chip._get_flowgraph_exit_nodes() == [('export', '0'), ('export', '1')]

#########################
if __name__ == "__main__":
    test_graph()
