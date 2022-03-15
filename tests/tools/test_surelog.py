import siliconcompiler

import os
import subprocess
import sys

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_surelog(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.set('flow', 'surelog')

    chip.run()

    assert chip.find_result('v', step=step) is not None

@pytest.mark.eda
@pytest.mark.quick
def test_surelog_preproc_regression(datadir):
    src = os.path.join(datadir, 'test_preproc.v')
    design = 'test_preproc'
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', src)
    chip.add('define', 'MEM_ROOT=test')
    chip.set('design', design)
    chip.set('mode', 'asicflow')
    chip.set('arg', 'step', step)
    chip.set('flow', 'surelog')

    chip.run()

    result = chip.find_result('v', step=step)

    assert result is not None

    with open(result, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()

@pytest.mark.eda
@pytest.mark.quick
def test_replay(scroot):
    src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.set('flow', 'surelog')
    chip.set('quiet', True)
    chip.set('eda', 'surelog', 'env', step, '0', 'SLOG_ENV', 'SUCCESS')

    chip.run()

    workdir = chip._getworkdir(step=step)
    if 'win' in sys.platform:
        script = 'replay.cmd'
        echo = 'if %errorlevel% neq 0 exit /b %errorlevel%\necho %SLOG_ENV%'
    else:
        script = './replay.sh'
        echo = 'echo $SLOG_ENV'

    with open(os.path.join(workdir, script), 'a') as f:
        f.write(echo + '\n')

    os.chdir(workdir)
    p = subprocess.run([script], stdout=subprocess.PIPE)

    assert p.returncode == 0
    assert p.stdout.decode('ascii').rstrip().split('\n')[-1] == 'SUCCESS'

if __name__ == "__main__":
    from tests.fixtures import scroot
    from tests.fixtures import datadir
    test_surelog(scroot())
    test_surelog_preproc_regression(datadir(__file__))
