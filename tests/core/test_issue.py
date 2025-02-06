import siliconcompiler

import pytest
import glob
import os
import pathlib


@pytest.mark.quick
@pytest.mark.eda
@pytest.mark.timeout(300)
def test_automatic_issue(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'global_placement', 'var', 'place_density', 'asdf',
                 step='place.global', index='0')

    gcd_chip.set('option', 'to', 'cts.clock_tree_synthesis')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
       assert gcd_chip.run()

    assert len(glob.glob(f'{gcd_chip.getworkdir()}/sc_issue*.tar.gz')) == 1

    with open(
            f'{gcd_chip.getworkdir(step="place.global", index="0")}/'
            'sc_place.global0.log') as f:
        text = f.read()
        assert "Collecting input sources" not in text
        assert "Copying " not in text


def test_relpath(gcd_chip):
    path = os.path.abspath('test.file')
    path = pathlib.PureWindowsPath(path).as_posix()
    with open(path, 'w') as f:
        f.write('test')

    gcd_chip.set('option', 'file', 'blah', path)
    gcd_chip._relative_path = os.getcwd()

    assert gcd_chip.find_files('option', 'file', 'blah') == ['test.file']

    gcd_chip._relative_path = None
    assert gcd_chip.find_files('option', 'file', 'blah') == [path]
