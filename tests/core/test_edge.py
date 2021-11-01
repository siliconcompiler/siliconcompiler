# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_edge():

    chip = siliconcompiler.Chip()

    syn_np = 10

    #nodes
    chip.node('import', 'surelog')
    for i in range(syn_np):
        chip.node('syn', 'yosys', index=i)
    chip.node('synmin', 'minimum')
    chip.node('floorplan', 'openroad')

    #edges
    for i in range(syn_np):
        chip.edge('import', 'syn', head_index=i)
        chip.edge('syn', 'synmin', tail_index=i)
    chip.edge('synmin', 'floorplan')
    chip.write_flowgraph('flow.png')
    assert os.path.isfile('flow.png')

#########################
if __name__ == "__main__":
    test_edge()
