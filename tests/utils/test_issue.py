import siliconcompiler

import pytest
import glob
import os
import pathlib
import tarfile


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_automatic_issue(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'global_placement', 'var', 'place_density', 'asdf',
                 step='place.global', index='0')

    gcd_chip.set('option', 'to', 'cts.clock_tree_synthesis')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run(raise_exception=True)

    assert len(glob.glob(f'{gcd_chip.getworkdir()}/sc_issue*.tar.gz')) == 1

    with open(
            f'{gcd_chip.getworkdir(step="place.global", index="0")}/'
            'sc_place.global_0.log') as f:
        text = f.read()
        assert "Collecting input sources" not in text
        assert "Copying " not in text

    tarball = glob.glob(f'{gcd_chip.getworkdir()}/sc_issue*.tar.gz')[0]
    with tarfile.open(tarball, 'r:gz') as tar:
        tar.extractall(path='.')

    archname = os.path.basename(tarball)
    foldername = archname[0:-7]
    assert os.path.isdir(foldername)
    assert os.path.isfile(os.path.join(foldername, 'run.sh'))


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
