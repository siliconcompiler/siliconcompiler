# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import re
import os

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_flowgraph():

    ################################################
    # Serial
    ################################################

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("freepdk45_asicflow")
    chip.writegraph('serial.png')

    ################################################
    # Fork-Join
    ################################################

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.set('flowarg','syn_np', "4")
    chip.set('flowarg','place_np', "4")
    chip.set('flowarg','route_np', "4")
    chip.target("freepdk45_asicflow")
    chip.writegraph('forkjoin.png')

    ################################################
    # Pipes
    ################################################

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.set('flowarg','np', "10")
    chip.target("freepdk45_dvflow")
    chip.writegraph('pipes.png')

    # basic compile to end check
    os.path.isfile('pipes.png')
    os.path.isfile('forkjoin.png')
    os.path.isfile('serial.png')

#########################
if __name__ == "__main__":
    test_flowgraph()
