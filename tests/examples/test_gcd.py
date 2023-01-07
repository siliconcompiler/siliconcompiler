import siliconcompiler

import os
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
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

    assert chip.get('tool', 'yosys', 'report', 'syn', '0', 'cellarea') == ['syn.log']

    # "No timescale set..."
    assert chip.get('metric', 'import', '0', 'warnings') == 10

    # "Found unsupported expression..." (x72) + 3 ABC Warnings
    assert chip.get('metric', 'syn', '0', 'warnings') == 75

    assert chip.get('metric', 'floorplan', '0', 'warnings') == 0

    assert chip.get('metric', 'physyn', '0', 'warnings') == 0

    assert chip.get('metric', 'place', '0', 'warnings') == 0

    # "1584 wires are pure wire and no slew degradation"
    # "Creating fake entries in the LUT"
    # "Could not find power special net" (x2)
    assert chip.get('metric', 'cts', '0', 'warnings') == 2

    assert chip.get('metric', 'route', '0', 'warnings') == 0

    assert chip.get('metric', 'dfm', '0', 'warnings') == 0

    # "no fill config specified"
    assert chip.get('metric', 'export', '0', 'warnings') == 1

@pytest.mark.eda
@pytest.mark.quick
def test_cli(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])
    assert proc.returncode == 0

@pytest.mark.eda
@pytest.mark.quick
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
    assert chip.get('metric', 'lvs', '0', 'drvs') == 0
    assert chip.get('metric', 'drc', '0', 'drvs') == 0

@pytest.mark.eda
@pytest.mark.skip(reason="asap7 not yet supported using new library scheme")
def test_cli_asap7(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run_asap7.sh')])
    assert proc.returncode == 0
