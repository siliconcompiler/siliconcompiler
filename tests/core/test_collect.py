import siliconcompiler
from siliconcompiler.targets import asic_demo
import os
import pytest
from pathlib import Path


@pytest.mark.nostrict
def test_collect_file_update():
    # Checks if collected files are properly updated after editing

    # Create instance of Chip class
    with open('fake.v', 'w') as f:
        f.write('fake')
    chip = siliconcompiler.Chip('fake')
    chip.input('fake.v')
    chip.collect()
    filename = chip.find_files('input', 'rtl', 'verilog')[0]

    assert len(os.listdir(chip._getcollectdir())) == 1

    with open(os.path.join(chip._getcollectdir(), filename), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun remote run
    chip.collect()
    assert len(os.listdir(chip._getcollectdir())) == 1

    with open(os.path.join(chip._getcollectdir(), filename), 'r') as f:
        assert f.readline() == 'newfake'


def test_collect_file_asic_demo():
    chip = siliconcompiler.Chip('demo')
    chip.use(asic_demo)
    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1

    for f in chip.find_files('input', 'rtl', 'verilog', step='import', index=0):
        assert f.startswith(chip._getcollectdir())


def test_collect_file_verbose(caplogger):
    chip = siliconcompiler.Chip('demo')
    chip.use(asic_demo)
    log = caplogger(chip)
    chip.collect()

    assert "Collecting input sources" in log()
    assert "Copying " in log()


def test_collect_directory():
    chip = siliconcompiler.Chip('demo')
    os.makedirs('testingdir', exist_ok=True)

    with open('testingdir/test', 'w') as f:
        f.write('test')

    chip.set('option', 'dir', 'check', 'testingdir')

    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1

    path = chip.find_files('option', 'dir', 'check')[0]
    assert path.startswith(chip._getcollectdir())
    assert os.path.basename(path).startswith('testingdir')
    assert os.path.basename(path) != 'testingdir'
    assert os.listdir(path) == ['test']


def test_collect_subdirectory():
    chip = siliconcompiler.Chip('demo')
    os.makedirs('testingdir/subdir', exist_ok=True)

    with open('testingdir/subdir/test', 'w') as f:
        f.write('test')

    chip.set('option', 'dir', 'check', 'testingdir')

    chip.collect()

    path = chip.find_files('option', 'dir', 'check')[0]
    assert path.startswith(chip._getcollectdir())
    assert os.path.basename(path).startswith('testingdir')
    assert os.path.basename(path) != 'testingdir'
    assert os.listdir(path) == ['subdir']
    assert os.listdir(os.path.join(path, 'subdir')) == ['test']


def test_collect_directory_filereference():
    chip = siliconcompiler.Chip('demo')
    os.makedirs('testingdir', exist_ok=True)

    with open('testingdir/test', 'w') as f:
        f.write('test')

    chip.set('option', 'dir', 'check', 'testingdir')
    chip.set('option', 'file', 'check', 'testingdir/test')

    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1

    path = chip.find_files('option', 'file', 'check')[0]
    assert path.startswith(chip._getcollectdir())
    assert os.path.basename(path) == 'test'


def test_collect_file_not_verbose(caplogger):
    chip = siliconcompiler.Chip('demo')
    chip.use(asic_demo)
    log = caplogger(chip)
    chip.collect(verbose=False)

    assert "Collecting input sources" not in log()
    assert "Copying " not in log()


def test_collect_file_with_false():
    chip = siliconcompiler.Chip('demo')
    chip.use(asic_demo)
    chip.set('input', 'rtl', 'verilog', False, field='copy')
    chip.collect()

    # No files should have been collected
    assert len(os.listdir(chip._getcollectdir())) == 0


def test_collect_file_home(monkeypatch):
    def _mock_home():
        return Path(os.getcwd())

    monkeypatch.setattr(Path, 'home', _mock_home)

    with open('test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', Path.home())
    chip.set('option', 'ydir', True, field='copy')
    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1
    assert len(os.listdir(chip.find_files('option', 'ydir')[0])) == 0


def test_collect_file_build():
    os.makedirs('build', exist_ok=True)

    with open('build/test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', 'build')
    chip.set('option', 'ydir', True, field='copy')
    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1
    assert len(os.listdir(chip.find_files('option', 'ydir')[0])) == 0


def test_collect_file_hidden_dir():
    os.makedirs('test/.test', exist_ok=True)

    with open('test/.test/test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', 'test')
    chip.set('option', 'ydir', True, field='copy')
    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1
    assert len(os.listdir(chip.find_files('option', 'ydir')[0])) == 0


def test_collect_file_hidden_file():
    os.makedirs('test', exist_ok=True)

    with open('test/.test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', 'test')
    chip.set('option', 'ydir', True, field='copy')
    chip.collect()

    assert len(os.listdir(chip._getcollectdir())) == 1
    assert len(os.listdir(chip.find_files('option', 'ydir')[0])) == 0


def test_collect_file_whitelist_error():
    os.makedirs('test/testing', exist_ok=True)

    with open('test/test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', 'test')
    chip.set('option', 'ydir', True, field='copy')

    with pytest.raises(RuntimeError):
        chip.collect(whitelist=[os.path.abspath('not_test_folder')])

    assert len(os.listdir(chip._getcollectdir())) == 0


def test_collect_file_whitelist_pass():
    os.makedirs('test/testing', exist_ok=True)

    with open('test/test', 'w') as f:
        f.write('test')

    chip = siliconcompiler.Chip('demo')
    chip.set('option', 'ydir', 'test')
    chip.set('option', 'ydir', True, field='copy')

    chip.collect(whitelist=[os.path.abspath('test')])

    assert len(os.listdir(chip._getcollectdir())) == 1
