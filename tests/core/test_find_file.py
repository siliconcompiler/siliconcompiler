# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import shutil
from unittest import mock

import pytest

import siliconcompiler

def test_find_sc_file(datadir):

    chip = siliconcompiler.Chip('test')

    assert chip._find_sc_file("flows/asicflow.py") is not None
    assert chip._find_sc_file("pdks/freepdk45.py") is not None

    chip.set('option', 'scpath', os.path.join(datadir, 'sclib'))
    assert chip._find_sc_file('test.txt') is not None

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah', missing_ok=True) is None

    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        assert chip._find_sc_file('my_file_that_doesnt_exist.blah') is None

def test_find_sc_file_env(datadir):
    '''Ensure we can find files on a custom path by setting the SCPATH env
    variable.'''
    chip = siliconcompiler.Chip('test')

    # assert precondition that we can't find this file by default
    assert chip._find_sc_file('test.txt', missing_ok=True) is None

    # check that we can find file after inserting sclib path into SCPATH env var
    env = {'SCPATH': os.path.join(datadir, 'sclib')}
    with mock.patch.dict(os.environ, env, clear=True):
        assert chip._find_sc_file('test.txt', missing_ok=True) is not None

def test_find_sc_file_relative(datadir):
    '''Ensure we can find files based on a relative path added to scpath.'''

    # copy sclib/ from datadir into this test's temporary working directory, so
    # we can reference it via relative path.
    shutil.copytree(os.path.join(datadir, 'sclib'), 'sclib')

    chip = siliconcompiler.Chip('test')

    assert chip._find_sc_file('test.txt', missing_ok=True) is None

    chip.set('option', 'scpath', 'sclib')

    assert chip._find_sc_file('test.txt', missing_ok=True) is not None

def test_find_sc_file_cwd():
    chip = siliconcompiler.Chip('test')
    mydir = os.getcwd()

    os.mkdir('test')
    os.chdir('test')
    # Should be relative to starting directory
    assert chip._find_sc_file('.') == mydir
    os.chdir(mydir)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_find_sc_file(datadir(__file__))
