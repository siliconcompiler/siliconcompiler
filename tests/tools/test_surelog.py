import siliconcompiler

import os
import sys

import pytest

from siliconcompiler.tools.surelog import parse
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_surelog(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "parse"

    chip = siliconcompiler.Chip(design)
    chip.load_target(freepdk45_demo)

    chip.input(gcd_src)
    chip.node('surelog', step, parse)
    chip.set('option', 'flow', 'surelog')

    chip.run()

    output = chip.find_result('v', step=step)
    assert output is not None


@pytest.mark.eda
@pytest.mark.quick
def test_surelog_duplicate_inputs(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "parse"

    chip = siliconcompiler.Chip(design)
    chip.load_target(freepdk45_demo)

    # Set duplicate input files.
    chip.input(gcd_src)
    chip.input(gcd_src)

    chip.set('option', 'clean', True)
    chip.node('surelog', step, parse)
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
    step = "parse"

    chip = siliconcompiler.Chip(design)
    chip.load_target(freepdk45_demo)
    chip.node('surelog', step, parse)
    chip.input(src)
    chip.add('option', 'define', 'MEM_ROOT=test')
    chip.set('option', 'flow', 'surelog')

    chip.run()

    result = chip.find_result('v', step=step)

    assert result is not None

    with open(result, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skipif(sys.platform == 'win32', reason='Replay script not supported on Windows')
def test_replay(scroot, run_cli):
    src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "parse"

    chip = siliconcompiler.Chip(design)
    chip.load_target(freepdk45_demo)

    chip.input(src)
    chip.node('surelog', step, parse)
    chip.set('option', 'flow', 'surelog')
    chip.set('option', 'quiet', True)
    chip.set('option', 'clean', True)  # replay should work even with clean=True
    chip.set('tool', 'surelog', 'task', step, 'env', 'SLOG_ENV', 'SUCCESS', step=step, index='0')

    chip.run()

    workdir = chip.getworkdir(step=step)
    script = os.path.join(workdir, 'replay.sh')
    echo = 'echo $SLOG_ENV'

    with open(script, 'a') as f:
        f.write(echo + '\n')

    proc = run_cli(script, stdout_to_pipe=True)

    assert proc.stdout.decode('ascii').rstrip().splitlines()[-1] == \
        'SUCCESS'


@pytest.mark.eda
@pytest.mark.quick
def test_github_issue_1789():
    chip = siliconcompiler.Chip('encode_stream_sc_module_8')
    chip.load_target(freepdk45_demo)

    i_file = os.path.join(os.path.dirname(__file__),
                          'data',
                          'gh1789',
                          'encode_stream_sc_module_8.v')

    chip.input(i_file)
    chip.set('option', 'to', ['import_verilog'])

    chip.run()

    i_file_data = None
    with open(i_file, 'r') as f:
        i_file_data = f.read()
    i_file_data = "\n".join(i_file_data.splitlines())

    o_file_data = None
    o_file = chip.find_result('v', step='import_verilog')
    with open(o_file, 'r') as f:
        o_file_data = f.read()

    # Remove SC header and footer
    o_file_data = "\n".join(o_file_data.splitlines()[3:-4])

    assert i_file_data == o_file_data


if __name__ == "__main__":
    from tests.fixtures import scroot
    from tests.fixtures import datadir
    test_surelog(scroot())
    test_surelog_duplicate_inputs(scroot())
    test_surelog_preproc_regression(datadir(__file__))
