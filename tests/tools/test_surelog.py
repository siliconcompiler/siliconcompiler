import siliconcompiler

import os
import subprocess
import sys

import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('clean', [False, True])
def test_surelog(scroot, clean):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(design)
    chip.load_target('freepdk45_demo')

    chip.add('input', 'rtl', 'verilog', gcd_src)
    chip.set('option', 'mode', 'sim')
    chip.set('option', 'clean', clean)
    chip.node('surelog', step, 'surelog')
    chip.set('option', 'flow', 'surelog')

    chip.run()

    output = chip.find_result('v', step=step)
    assert output is not None

    # slpp_all/ should only exist when clean is False
    workdir = '/'.join(output.split('/')[:-2])
    intermediate_dir = os.path.join(workdir, 'slpp_all')
    assert os.path.isdir(intermediate_dir) != clean

@pytest.mark.eda
@pytest.mark.quick
def test_surelog_duplicate_inputs(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(design)
    chip.load_target('freepdk45_demo')

    # Set duplicate input files.
    chip.add('input', 'rtl', 'verilog', gcd_src)
    chip.add('input', 'rtl', 'verilog', gcd_src)

    chip.set('option', 'mode', 'sim')
    chip.set('option', 'clean', True)
    chip.node('surelog', step, 'surelog')
    chip.set('option', 'flow', 'surelog')

    chip.run()

    output = chip.find_result('v', step=step)
    assert output is not None

    # Ensure only one module is written to the output Verilog. (Two will be written if dedup fails)
    module_count = 0
    with open(output, 'r') as rf:
        for line in rf.readlines():
            if line.startswith('module gcd'):
                module_count += 1
    assert module_count == 1

@pytest.mark.eda
@pytest.mark.quick
def test_surelog_preproc_regression(datadir):
    src = os.path.join(datadir, 'test_preproc.v')
    design = 'test_preproc'
    step = "import"

    chip = siliconcompiler.Chip(design)
    chip.load_target('freepdk45_demo')
    chip.node('surelog', step, 'surelog')
    chip.add('input', 'rtl', 'verilog', src)
    chip.add('option', 'define', 'MEM_ROOT=test')
    chip.set('option', 'mode', 'sim')
    chip.set('option', 'flow', 'surelog')

    chip.run()

    result = chip.find_result('v', step=step)

    assert result is not None

    with open(result, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skipif(sys.platform=='win32', reason='Replay script not supported on Windows')
def test_replay(scroot):
    src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(design)
    chip.load_target('freepdk45_demo')

    chip.add('input', 'rtl', 'verilog', src)
    chip.set('option', 'mode', 'sim')
    chip.node('surelog', step, 'surelog')
    chip.set('option', 'flow', 'surelog')
    chip.set('option', 'quiet', True)
    chip.set('option', 'clean', True) # replay should work even with clean=True
    chip.set('tool', 'surelog', 'env', step, '0', 'SLOG_ENV', 'SUCCESS')

    chip.run()

    workdir = chip._getworkdir(step=step)
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
    test_surelog_duplicate_inputs(scroot())
    test_surelog_preproc_regression(datadir(__file__))
