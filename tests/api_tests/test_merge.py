# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

from siliconcompiler.schema import schema_flowgraph
from siliconcompiler.schema import schema_cfg

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_merge():

    chip = siliconcompiler.Chip()

    # big default dict
    default_cfg = schema_cfg()
    new_cfg = {}
    new_cfg  = schema_flowgraph(new_cfg, step='syn')
    merged_cfg = chip.merge(default_cfg, new_cfg)
    chip.writecfg("merged.json", cfg=merged_cfg)

    assert (os.path.isfile('merged.json'))

#########################
if __name__ == "__main__":
    test_merge()
