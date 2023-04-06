import siliconcompiler

import os
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py(setup_example_test):
    setup_example_test('gcd')

    import gcd
    gcd.main()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that report file was generated.
    assert os.path.isfile('build/gcd/job0/report.html')

    manifest = 'build/gcd/job0/export/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)

    # Ensure hashes for tool outputs are stored and persist
    assert len(chip.get('tool', 'openroad', 'task', 'dfm', 'output', step='dfm', index=0, field='filehash')) == 4
    assert len(chip.get('tool', 'openroad', 'task', 'dfm', 'output', step='dfm', index=0)) == 4

    assert chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea', step='syn', index='0') == ['reports/stat.json']

    # "No timescale set..."
    assert chip.get('metric', 'warnings', step='import', index='0') == 10

    # "Found unsupported expression..." (x72) + 3 ABC Warnings
    assert chip.get('metric', 'warnings', step='syn', index='0') == 75

    # [WARNING PSM*]
    assert chip.get('metric', 'warnings', step='floorplan', index='0') == 16

    assert chip.get('metric', 'warnings', step='physyn', index='0') == 0

    assert chip.get('metric', 'warnings', step='place', index='0') == 0

    # "1632 wires are pure wire and no slew degradation"
    # "Creating fake entries in the LUT"
    assert chip.get('metric', 'warnings', step='cts', index='0') == 2

    # Missing route to pin (x69)
    assert chip.get('metric', 'warnings', step='route', index='0') == 69

    # Missing route to pin (x235)
    assert chip.get('metric', 'warnings', step='dfm', index='0') == 235

    # "no fill config specified"
    assert chip.get('metric', 'warnings', step='export', index='0') == 1

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_cli(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])
    assert proc.returncode == 0

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_sky130(setup_example_test):
    setup_example_test('gcd')

    import gcd_skywater
    gcd_skywater.main()

    assert os.path.isfile('build/gcd/rtl2gds/export/0/outputs/gcd.gds')

    manifest = 'build/gcd/signoff/signoff/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'drvs', step='lvs', index='0') == 0
    assert chip.get('metric', 'drvs', step='drc', index='0') == 0

@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.skip(reason='Long runtime, can still timeout at 900s')
def test_cli_asap7(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run_asap7.sh')])
    assert proc.returncode == 0
