# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_edge():

    chip = siliconcompiler.Chip()

    syn_np = 10

    #nodes
    chip.node('import', 'surelog')
    chip.node('syn', 'yosys', n=syn_np)
    chip.node('synmin', 'minimum')
    chip.node('floorplan', 'openroad')

    #edges
    chip.edge('import', 'syn', nhead=syn_np)
    chip.edge('syn', 'synmin', ntail=syn_np)
    chip.edge('synmin', 'floorplan')

    chip.write_flowgraph('flow.png')
    assert os.path.isfile('flow.png')

#########################
if __name__ == "__main__":
    test_edge()
