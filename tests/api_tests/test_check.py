# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

def test_api_check():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("freepdk45_asicflow")
    chip.set('source', 'examples/gcd/gcd.v')

    assert (chip.check() == 0)

#########################
if __name__ == "__main__":
    test_api_check()
