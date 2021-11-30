# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import pytest
@pytest.mark.skip(reason="broken file path")
def test_archive():
    scroot = os.path.abspath(os.path.join(os.path.dirname(__file__),"..",".."))
    srcdir = os.path.join(scroot,
                          'third_party',
                          'designs',
                          'oh',
                          'stdlib',
                          'hdl')

    chip = siliconcompiler.Chip()
    chip.set('design', 'oh_add')
    chip.set('source', os.path.join(srcdir,'oh_add.v'))
    chip.set('steplist','import')
    chip.target('asicflow_freepdk45')
    chip.run()
    chip.archive()

#########################
if __name__ == "__main__":
    test_archive()
