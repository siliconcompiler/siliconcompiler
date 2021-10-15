# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import siliconcompiler
import importlib


if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_verilator():

    ydir = (os.path.dirname(os.path.abspath(__file__)) +
            "/../../third_party/designs/oh/stdlib/hdl")

    design = "oh_fifo_sync"
    topfile = ydir + "/" + design + ".v"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.set('ydir', ydir)
    chip.set('design', design)
    chip.set('source', topfile)
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('mode', 'sim')
    chip.set('arg','step',step)
    chip.target("verilator")
    chip.run()

    # check that compilation succeeded
    assert chip.find_result('v', step=step) is not None

#########################
if __name__ == "__main__":
    test_verilator()
