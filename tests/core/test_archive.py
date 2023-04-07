# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_archive(oh_dir):
    srcdir = os.path.join(oh_dir, 'stdlib', 'hdl')

    chip = siliconcompiler.Chip('oh_parity')
    chip.input(os.path.join(srcdir,'oh_parity.v'))
    chip.set('option', 'steplist', 'import')
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.archive()

    assert os.path.isfile('oh_parity_job0.tgz')

#########################
if __name__ == "__main__":
    test_archive()
