import siliconcompiler

from siliconcompiler.tools.surelog import parse
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

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import join
from siliconcompiler.tools.builtin import minimum

from tests.core.tools.fake import fake_in
from tests.core.tools.fake import fake_out


def test_graph():

    chip = siliconcompiler.Chip('test')

    # RTL
    chip.pipe('rtl', [{'import': parse},
                      {'syn': syn_asic},
                      {'export': nop}])

    # APR
    chip.pipe('apr', [{'import': nop},
                      {'floorplan': floorplan},
                      {'physyn': physyn},
                      {'place': place},
                      {'cts': cts},
                      {'route': route},
                      {'dfm': dfm},
                      {'export': export}])

    # SIGNOFF
    chip.node('signoff', 'import', nop)
    chip.node('signoff', 'extspice', extspice)
    chip.node('signoff', 'drc', drc)
    chip.node('signoff', 'lvs', lvs)
    chip.node('signoff', 'export', join)

    chip.edge('signoff', 'import', 'drc')
    chip.edge('signoff', 'import', 'extspice')
    chip.edge('signoff', 'extspice', 'lvs')
    chip.edge('signoff', 'lvs', 'export')
    chip.edge('signoff', 'drc', 'export')

    # TOP
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
    chip.node(flow, 'premin', fake_out, index=0)
    chip.node(flow, 'premin', fake_out, index=1)
    chip.node(flow, 'domin', minimum)
    chip.node(flow, 'postmin', fake_in)

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    assert chip._get_flowgraph_entry_nodes(flow) == [('premin', '0'), ('premin', '1')]


def test_graph_exit():

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    assert chip._get_flowgraph_exit_nodes(chip.get('option', 'flow')) == [('export', '0'), ('export', '1')]


def test_graph_exit_with_steplist():

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    steps = ['import', 'syn', 'floorplan']

    assert chip._get_flowgraph_exit_nodes(chip.get('option', 'flow'), steplist=steps) == [('floorplan', '0')]


#########################
if __name__ == "__main__":
    test_graph()
