# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_api_minimum():
    '''API test for mux() method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()
    chip.set("design", "oh_add")
    chip.target("freepdk45_asicflow")

    # parallel syn step, all others single shot
    N = 10
    chip.set('flowgraph', 'syn', 'nproc', N)

    # resetting all results
    for step in chip.getkeys('flowgraph'):
        for index in range(chip.get('flowgraph', step, 'nproc')):
            for metric in chip.getkeys('metric', 'default', 'default', chip=chip):
                chip.set('metric', step, str(index), metric, 'real', 0, chip=chip)

    # creating fake syn results
    for i in range(N):
        for metric in chip.getkeys('metric', 'default', 'default', chip=chip):
            chip.set('metric', 'syn', str(i), metric, 'real', 1000-i*10, chip=chip)

    # select minimum
    for step in chip.getkeys('flowgraph'):
        min_index = chip.minimum(step)
        chip.set('flowstatus', step, 'select', min_index)

    # visual summary
    chip.summary()

    # expected result
    assert chip.get('flowstatus', 'syn', index, 'select') == 9

#########################
if __name__ == "__main__":
    test_api_minimum()
