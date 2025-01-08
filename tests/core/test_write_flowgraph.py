# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

from siliconcompiler.flows import dvflow
from siliconcompiler.targets import freepdk45_demo


def test_write_flowgraph_serial():

    ################################################
    # Serial
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)
    chip.write_flowgraph('serial.png')

    assert os.path.isfile('serial.png')


def test_write_flowgraph_forkjoin():

    ################################################
    # Fork-Join
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo, syn_np=4, place_np=4, route_np=4)
    chip.write_flowgraph('forkjoin.png')

    assert os.path.isfile('forkjoin.png')


def test_write_flowgraph_pipes():

    ################################################
    # Pipes
    ################################################

    chip = siliconcompiler.Chip('test')
    chip.use(dvflow, np=10)
    chip.set('option', 'flow', 'dvflow')
    chip.write_flowgraph('pipes.png')

    assert os.path.isfile('pipes.png')
