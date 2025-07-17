# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import init_floorplan

from siliconcompiler.tools.builtin import minimum


def test_edge(has_graphviz):
    chip = siliconcompiler.Chip('test')

    syn_np = 10

    flow = 'test'
    chip.set('option', 'flow', flow)
    # nodes
    chip.node(flow, 'import', parse)
    for i in range(syn_np):
        chip.node(flow, 'syn', syn_asic, index=i)
    chip.node(flow, 'synmin', minimum)
    chip.node(flow, 'floorplan', init_floorplan)

    # edges
    for i in range(syn_np):
        chip.edge(flow, 'import', 'syn', head_index=i)
        chip.edge(flow, 'syn', 'synmin', tail_index=i)
    chip.edge(flow, 'synmin', 'floorplan')
    chip.write_flowgraph('flow.png')
    assert os.path.isfile('flow.png')
