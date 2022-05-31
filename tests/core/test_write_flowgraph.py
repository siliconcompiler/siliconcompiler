# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_write_flowgraph():

    ################################################
    # Serial
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')
    chip.write_flowgraph('serial.png')

    assert os.path.isfile('serial.png')

    ################################################
    # Fork-Join
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.set('arg', 'flow', 'syn_np', "4")
    chip.set('arg', 'flow', 'place_np', "4")
    chip.set('arg', 'flow', 'route_np', "4")
    chip.load_target('freepdk45_demo')
    chip.write_flowgraph('forkjoin.png')

    assert os.path.isfile('forkjoin.png')

    ################################################
    # Pipes
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.set('arg', 'flow', 'np', "10")
    chip.load_pdk('freepdk45')
    chip.load_flow('dvflow')
    chip.set('option', 'flow', 'dvflow')
    chip.write_flowgraph('pipes.png')

    assert os.path.isfile('pipes.png')

#########################
if __name__ == "__main__":
    test_write_flowgraph()
