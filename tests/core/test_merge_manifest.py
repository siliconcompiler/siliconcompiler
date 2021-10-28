# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import copy
import siliconcompiler

from siliconcompiler.schema import schema_flowgraph
from siliconcompiler.schema import schema_cfg

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_merge_manifest():

    chip = siliconcompiler.Chip()

    # dict to merge in
    new_cfg = {}
    new_cfg  = schema_flowgraph(new_cfg, step='syn')
    # fill in a value so we can test merge
    new_cfg['flowgraph']['syn']['0'] = copy.deepcopy(new_cfg['flowgraph']['syn']['default'])
    new_cfg['flowgraph']['syn']['0']['tool']['value'] = 'yosys'

    chip.merge_manifest(new_cfg)
    chip.write_manifest("merged.json")

    assert (os.path.isfile('merged.json'))
    # ensure our value is reflected in chip's cfg
    assert chip.get('flowgraph', 'syn', '0', 'tool') == 'yosys'

#########################
if __name__ == "__main__":
    test_merge_manifest()
