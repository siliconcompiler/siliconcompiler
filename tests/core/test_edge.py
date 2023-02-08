# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_edge():

    chip = siliconcompiler.Chip('test')

    syn_np = 10

    flow = 'test'
    chip.set('option', 'flow', flow)
    #nodes
    chip.node(flow, 'import', 'surelog', 'import')
    for i in range(syn_np):
        chip.node(flow, 'syn', 'yosys', 'syn', index=i)
    chip.node(flow, 'synmin', 'minimum', 'synmin')
    chip.node(flow, 'floorplan', 'openroad', 'floorplan')

    #edges
    for i in range(syn_np):
        chip.edge(flow, 'import', 'syn', head_index=i)
        chip.edge(flow, 'syn', 'synmin', tail_index=i)
    chip.edge(flow, 'synmin', 'floorplan')
    chip.write_flowgraph('flow.png')
    assert os.path.isfile('flow.png')

#########################
if __name__ == "__main__":
    test_edge()
