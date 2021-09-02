# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_asicflow():

    chip = siliconcompiler.Chip(loglevel="DEBUG")
    chip.target("freepdk45_asicflow")
    chip.hash('import')

    a = True

    assert a

#########################
if __name__ == "__main__":
    sys.exit(main())
