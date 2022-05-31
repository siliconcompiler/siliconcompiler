# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import copy
import json
import siliconcompiler

from siliconcompiler.schema import schema_flowgraph

def test_merge_manifest():

    chip = siliconcompiler.Chip('test')

    # dict to merge in
    flow = 'test'
    new_cfg = {}
    new_cfg  = schema_flowgraph(new_cfg)
    # fill in a value so we can test merge
    new_cfg['flowgraph'][flow] = {}
    new_cfg['flowgraph'][flow]['syn'] = {}
    new_cfg['flowgraph'][flow]['syn']['0'] = copy.deepcopy(new_cfg['flowgraph']['default']['default']['default'])
    new_cfg['flowgraph'][flow]['syn']['0']['tool']['value'] = 'yosys'
    new_cfg['flowgraph'][flow]['syn']['0']['timeout']['value'] = 0

    chip.merge_manifest(new_cfg)
    chip.write_manifest("merged.json")

    assert (os.path.isfile('merged.json'))
    # ensure our value is reflected in chip's cfg
    assert chip.get('flowgraph', flow, 'syn', '0', 'tool') == 'yosys'

#########################
if __name__ == "__main__":
    test_merge_manifest()
