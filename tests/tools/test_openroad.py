# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import siliconcompiler
import importlib


if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_openroad():

    localdir = os.path.dirname(os.path.abspath(__file__))

    netlist = f"{localdir}/../data/oh_fifo_sync_freepdk45.vg"
    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip()
    chip.set('design', design)
    chip.set('netlist', netlist)
    chip.set('mode', 'asic')
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.target("openroad_floorplan")
    func = chip.loadfunction('freepdk45', 'pdk', 'setup_pdk')
    func(chip)
    chip.run()

    # check that compilation succeeded
    assert os.path.isfile(f"build/{design}/job0/floorplan0/outputs/{design}.def")

#########################
if __name__ == "__main__":
    test_openroad()
