import os
import pathlib
import pytest

from siliconcompiler import Chip


@pytest.mark.win32
def test_windows_path_compat():
    '''
    Test that SC stores POSIX-style paths internally, while still
    providing Windows-style paths when necessary on a Windows system.
    '''

    # Create a test file using Windows file paths.
    os.makedirs('d:\\\\windows_dir', exist_ok=True)
    windows_path = 'd:\\\\windows_dir\\windows_file.v'
    windows_content = '// Test file'
    with open(windows_path, 'w') as wf:
        wf.write(windows_content)

    # Create a Schema, and set the file path using Windows notation.
    chip = Chip('path_test')
    chip.input(windows_path)

    # Verify that the Schema path is POSIX-style.
    path = chip.get('input', 'rtl', 'verilog')[0]
    assert path == pathlib.Path(windows_path).as_posix()

    # Verify that SC still uses the Windows path on a Windows system.
    win_path = chip.find_files('input', 'rtl', 'verilog')[0]
    assert os.path.isfile(win_path)
    with open(win_path, 'r') as rf:
        assert rf.read() == windows_content
