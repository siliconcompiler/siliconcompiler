# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import shutil
import pathlib
from unittest import mock

import pytest

import siliconcompiler
from siliconcompiler.core import SiliconCompilerError


def test_find_sc_file(datadir):

    chip = siliconcompiler.Chip('test')

    assert chip._find_sc_file("flows/asicflow.py") is not None
    assert chip._find_sc_file("pdks/freepdk45.py") is not None

    chip.set('option', 'scpath', os.path.join(datadir, 'sclib'))
    assert chip._find_sc_file('test.txt') is not None

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah', missing_ok=True) is None

    with pytest.raises(SiliconCompilerError):
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


def test_invalid_script():
    '''Regression test: find_files(missing_ok=False) should error out if script
    not found.'''
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('tool', 'yosys', 'task', 'syn_asic', 'script', 'fakescript.tcl')

    with pytest.raises(SiliconCompilerError):
        chip.find_files('tool', 'yosys', 'task', 'syn_asic', 'script',
                        missing_ok=False, step='syn', index='0')


@pytest.mark.nostrict
def test_windows_path_relative():
    '''
    Test that SC can resolve a windows path on any OS
    '''

    # Create a test file using Windows file paths.
    path = os.path.join('testpath', 'testfile.v')
    path_as_windows = str(pathlib.PureWindowsPath(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as wf:
        wf.write('// Test file')

    # Create a Schema, and set the file path using Windows notation.
    chip = siliconcompiler.Chip('test')
    chip.input(path_as_windows)

    # Verify that the Schema path is unmodified.
    assert chip.get('input', 'rtl', 'verilog') == [path_as_windows]

    # Verify that SC can find the file regardless of the os
    check_files = chip.find_files('input', 'rtl', 'verilog')
    assert check_files
    assert os.path.isfile(check_files[0])


@pytest.mark.nostrict
def test_windows_path_imported_file():
    '''
    Test that SC can resolve a windows path on any OS
    '''

    # Create a test file using Windows file paths.
    path = r'C:\sc-test\testpath\testfile.v'

    # Create a Schema, and set the file path using Windows notation.
    chip = siliconcompiler.Chip('test')
    chip.input(path)

    path_hash = '555973cd01971eb31ae7dee374d147d075459b4a'
    import_path = os.path.join(chip._getcollectdir(), f'testfile_{path_hash}.v')

    os.makedirs(os.path.dirname(import_path), exist_ok=True)
    with open(import_path, 'w') as wf:
        wf.write('// Test file')

    # Verify that the Schema path is unmodified.
    assert chip.get('input', 'rtl', 'verilog') == [path]

    # Verify that SC can find the file
    check_files = chip.find_files('input', 'rtl', 'verilog')
    assert check_files
    assert check_files[0] == import_path
    assert os.path.isfile(check_files[0])


@pytest.mark.nostrict
def test_windows_path_imported_directory():
    '''
    Test that SC can resolve a windows path on any OS
    '''

    # Create a test file using Windows file paths.
    path = r'C:\sc-test\testpath\testfile.v'

    # Create a Schema, and set the file path using Windows notation.
    chip = siliconcompiler.Chip('test')
    chip.input(path)

    path_hash = 'ed19a25d5702e8b39dcd72d51bcc8ea787cedeb1'
    import_path = os.path.join(chip._getcollectdir(), f'testpath_{path_hash}', 'testfile.v')

    os.makedirs(os.path.dirname(import_path), exist_ok=True)
    with open(import_path, 'w') as wf:
        wf.write('// Test file')

    # Verify that the Schema path is unmodified.
    assert chip.get('input', 'rtl', 'verilog') == [path]

    # Verify that SC can find the file
    check_files = chip.find_files('input', 'rtl', 'verilog')
    assert check_files
    assert check_files[0] == import_path
    assert os.path.isfile(check_files[0])


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_find_sc_file(datadir(__file__))
