import siliconcompiler

import os
import subprocess
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_multiflow():

    chip = siliconcompiler.Chip('gcd')
    chip.load_target("skywater130_demo")

    #RTL
    chip.pipe('rtl', [{'import' : 'surelog'},
                      {'syn' : 'yosys'},
                      {'export' : 'nop'},])

    #APR
    chip.pipe('apr', [{'import' : 'nop'},
                      {'floorplan' : 'openroad'},
                      {'physyn' : 'openroad'},
                      {'place' : 'openroad'},
                      {'cts' : 'openroad'},
                      {'route' : 'openroad'},
                      {'dfm' : 'openroad'},
                      {'export' : 'klayout'}])

    #SIGNOFF
    chip.node('signoff', 'import', 'nop')
    chip.node('signoff', 'extspice', 'magic')
    chip.node('signoff', 'drc', 'magic')
    chip.node('signoff', 'lvs', 'netgen')
    chip.node('signoff', 'export', 'join')

    chip.edge('signoff', 'import', 'drc')
    chip.edge('signoff', 'import', 'extspice')
    chip.edge('signoff', 'extspice', 'lvs')
    chip.edge('signoff', 'lvs', 'export')
    chip.edge('signoff', 'drc', 'export')

    #TOP
    chip.graph("top","rtl", name="rtl")
    chip.graph("top","apr", name="apr")
    chip.graph("top","signoff", name="dv")
    chip.edge("top", "rtl", "apr")
    chip.edge("top", "apr", "dv")


    chip.add('source', 'gcd.v')
    chip.add('constraint', 'gcd.sdc')
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('track', True)


    datadir = os.path.join(os.path.dirname(__file__), 'data')

    setup_example_test('gcd')




    import gcd
    gcd.main()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that report file was generated.
    assert os.path.isfile('build/gcd/job0/report.html')

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

    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

    manifest = 'build/gcd/signoff/signoff/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip()
    chip.read_manifest(manifest)

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'lvs', '0', 'errors', 'real') == 0
    assert chip.get('metric', 'drc', '0', 'errors', 'real') == 0

@pytest.mark.eda
def test_cli_asap7(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run_asap7.sh')])
    assert proc.returncode == 0
