# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import siliconcompiler
import importlib


if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_ghdl():
    design = "adder"
    localdir = os.path.dirname(os.path.abspath(__file__))
    design_src = f"{localdir}/../data/{design}.vhdl"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.set('source', design_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg','step','import')
    chip.target('ghdl')
    chip.run()

    # check that compilation succeeded
    assert os.path.isfile(f"build/{design}/job0/import0/outputs/{design}.v")

#########################
if __name__ == "__main__":
    test_ghdl()
