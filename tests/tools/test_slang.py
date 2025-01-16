import os
import pytest

import siliconcompiler
from siliconcompiler.tools.slang import lint
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.quick
@pytest.mark.eda
def test_lint(scroot):
    chip = siliconcompiler.Chip('heartbeat')

    v_src = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    chip.input(v_src)

    flow = 'lint'
    chip.node(flow, 'lint', lint)
    chip.set('option', 'flow', flow)

    chip.run()

    assert chip.get('metric', 'errors', step='lint', index='0') == 0
    assert chip.get('metric', 'warnings', step='lint', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
def test_surelog(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "elaborate"

    chip = siliconcompiler.Chip(design)
    chip.use(freepdk45_demo)

    chip.input(gcd_src)
    chip.node('slang', step, elaborate)
    chip.set('option', 'flow', 'slang')

    chip.run()

    output = chip.find_result('v', step=step)
    assert output is not None


@pytest.mark.eda
@pytest.mark.quick
def test_surelog_duplicate_inputs(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "elaborate"

    chip = siliconcompiler.Chip(design)
    chip.use(freepdk45_demo)

    # Set duplicate input files.
    chip.input(gcd_src)
    chip.input(gcd_src)

    chip.set('option', 'clean', True)
    chip.node('slang', step, elaborate)
    chip.set('option', 'flow', 'slang')

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
    step = "elaborate"

    chip = siliconcompiler.Chip(design)
    chip.use(freepdk45_demo)
    chip.node('slang', step, elaborate)
    chip.input(src)
    chip.add('option', 'define', 'MEM_ROOT=test')
    chip.set('option', 'flow', 'slang')

    chip.run()

    result = chip.find_result('v', step=step)

    assert result is not None

    with open(result, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()


@pytest.mark.eda
@pytest.mark.quick
def test_github_issue_1789():
    chip = siliconcompiler.Chip('encode_stream_sc_module_8')
    chip.use(freepdk45_demo)

    i_file = os.path.join(os.path.dirname(__file__),
                          'data',
                          'gh1789',
                          'encode_stream_sc_module_8.v')

    chip.input(i_file)
    chip.set('option', 'to', ['import.verilog'])
    chip.node('slang', "import.verilog", elaborate)
    chip.set('option', 'flow', 'slang')

    chip.run()

    i_file_data = None
    with open(i_file, 'r') as f:
        i_file_data = f.read()
    i_file_data = "\n".join(i_file_data.splitlines())
    i_file_data += "\n\n"

    o_file_data = None
    o_file = chip.find_result('v', step='import.verilog')
    with open(o_file, 'r') as f:
        o_file_data = f.read()

    for l0, l1 in zip(i_file_data.splitlines(), o_file_data.splitlines()):
        print(l0, l1)

    assert i_file_data == o_file_data
