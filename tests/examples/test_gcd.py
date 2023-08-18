import siliconcompiler

import os
import subprocess

import pytest


def __check_gcd(chip):
    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that report file was generated.
    assert os.path.isfile('build/gcd/job0/report.html')

    # Ensure hashes for tool outputs are stored and persist
    assert len(chip.get('tool', 'openroad', 'task', 'dfm', 'output',
                        step='dfm', index=0, field='filehash')) == 4
    assert len(chip.get('tool', 'openroad', 'task', 'dfm', 'output',
                        step='dfm', index=0)) == 4

    assert chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                    step='syn', index='0') == ['reports/stat.json']

    # "No timescale set..."
    assert chip.get('metric', 'warnings', step='import', index='0') == 10

    # "Found unsupported expression..." (x72) + 3 ABC Warnings
    assert chip.get('metric', 'warnings', step='syn', index='0') == 75

    # Warning: *. (x3)
    # [WARNING PSM*] (x12)
    assert chip.get('metric', 'warnings', step='floorplan', index='0') == 15

    # Warning: *. (x5)
    assert chip.get('metric', 'warnings', step='place', index='0') == 5

    # Warning: *. (x3)
    # "1632 wires are pure wire and no slew degradation"
    # "Creating fake entries in the LUT"
    assert chip.get('metric', 'warnings', step='cts', index='0') == 5

    # Warning: *. (x3)
    # Missing route to pin (x70)
    assert chip.get('metric', 'warnings', step='route', index='0') == 73

    # Warning: *. (x3)
    # Missing route to pin (x185)
    assert chip.get('metric', 'warnings', step='dfm', index='0') == 186

    # "no fill config specified"
    assert chip.get('metric', 'warnings', step='export', index='0') == 1


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py(setup_example_test):
    setup_example_test('gcd')

    import gcd
    gcd.main()

    manifest = 'build/gcd/job0/export/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)

    __check_gcd(chip)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_read_manifest(scroot):
    '''
    Test that running from manifest generates the same result
    '''
    chip = siliconcompiler.Chip('gcd')
    chip.input(f"{scroot}/examples/gcd/gcd.v")
    chip.input(f"{scroot}/examples/gcd/gcd.sdc")
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'hash', True)
    chip.set('option', 'novercheck', True)
    chip.set('option', 'nodisplay', True)
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])
    chip.load_target("freepdk45_demo")

    chip.write_manifest('./test.json')
    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest('./test.json')
    chip.run()
    chip.summary()

    __check_gcd(chip)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_cli(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])
    assert proc.returncode == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(900)
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
