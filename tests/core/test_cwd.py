# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest
import shutil
import siliconcompiler

@pytest.mark.quick
@pytest.mark.skipif(sys.platform=='win32', reason='Windows throws a permission denied error if we try to delete a directory which a process is currently inhabiting.')
def test_cwd():
    os.mkdir('tmp_test_cwd')
    os.chdir('tmp_test_cwd')
    shutil.rmtree('../tmp_test_cwd')

    # The act of creating a Chip object should raise a SiliconCompilerError
    # if the current working directory does not exist.
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip = siliconcompiler.Chip('my_design')

#########################
if __name__ == "__main__":
    test_cwd()
