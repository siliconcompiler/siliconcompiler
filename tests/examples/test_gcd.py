import siliconcompiler
import os
import pytest
from siliconcompiler.targets import freepdk45_demo


def __check_gcd(chip):
    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
    # Verify that final manifest was recorded.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')

    # Ensure hashes for tool outputs are stored and persist
    assert len(chip.get('tool', 'openroad', 'task', 'detailed_route', 'output',
                        step='route.detailed', index=0, field='filehash')) == 4
    assert len(chip.get('tool', 'openroad', 'task', 'detailed_route', 'output',
                        step='route.detailed', index=0)) == 4

    assert chip.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                    step='syn', index='0') == ['reports/stat.json']

    # "No timescale set..."
    assert chip.get('metric', 'warnings', step='import.verilog', index='0') == 7

    # 2 ABC Warnings
    assert chip.get('metric', 'warnings', step='syn', index='0') == 2

    assert chip.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    assert chip.get('metric', 'warnings', step='place.detailed', index='0') == 0

    assert chip.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 1

    assert chip.get('metric', 'warnings', step='route.global', index='0') == 0

    assert chip.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert chip.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_gcd():
    from gcd import gcd
    gcd.main()

    manifest = 'build/gcd/job0/gcd.pkg.json'
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
    chip.set('option', 'quiet', True)
    chip.set('option', 'track', True)
    chip.set('option', 'hash', True)
    chip.set('option', 'nodisplay', True)
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])
    chip.use(freepdk45_demo)

    chip.write_manifest('./test.json')
    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest('./test.json')
    assert chip.run()
    chip.summary()

    __check_gcd(chip)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_sh_run(examples_root, run_cli):
    run_cli(os.path.join(examples_root, 'gcd', 'run.sh'),
            'build/gcd/job0/write.gds/0/outputs/gcd.gds')


@pytest.mark.eda
@pytest.mark.timeout(900)
def test_py_gcd_skywater():
    from gcd import gcd_skywater
    gcd_skywater.main()

    assert os.path.isfile('build/gcd/rtl2gds/write.gds/0/outputs/gcd.gds')

    manifest = 'build/gcd/signoff/signoff/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'drcs', step='lvs', index='0') == 0
    assert chip.get('metric', 'drcs', step='drc', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(900)
def test_py_gcd_gf180():
    from gcd import gcd_gf180
    gcd_gf180.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')


@pytest.mark.eda
@pytest.mark.timeout(900)
def test_py_gcd_screenshot(monkeypatch):
    from gcd import gcd
    gcd.main()

    manifest = 'build/gcd/job0/gcd.pkg.json'
    assert os.path.isfile(manifest)

    policy = os.path.abspath('policy.xml')

    monkeypatch.setenv("MAGICK_CONFIGURE_PATH", os.path.dirname(policy))
    with open(policy, 'w') as f:
        f.write('<policy domain="resource" name="memory" value="8GiB"/>\n')
        f.write('<policy domain="resource" name="map" value="8GiB"/>\n')
        f.write('<policy domain="resource" name="width" value="32KP"/>\n')
        f.write('<policy domain="resource" name="height" value="32KP"/>\n')
        f.write('<policy domain="resource" name="area" value="1GP"/>\n')
        f.write('<policy domain="resource" name="disk" value="8GiB"/>\n')

    from gcd import gcd_screenshot
    gcd_screenshot.main(manifest)

    assert os.path.isfile('build/gcd/highres/screenshot/0/outputs/gcd_X0_Y0.png')
    assert os.path.isfile('build/gcd/highres/screenshot/0/outputs/gcd_X0_Y1.png')
    assert os.path.isfile('build/gcd/highres/screenshot/0/outputs/gcd_X1_Y0.png')
    assert os.path.isfile('build/gcd/highres/screenshot/0/outputs/gcd_X1_Y1.png')
    assert os.path.isfile('build/gcd/highres/merge/0/outputs/gcd.png')


@pytest.mark.eda
@pytest.mark.timeout(900)
def test_sh_run_asap7(examples_root, run_cli):
    run_cli(os.path.join(examples_root, 'gcd', 'run_asap7.sh'),
            'build/gcd/job0/write.gds/0/outputs/gcd.gds')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_gcd_sta():
    from gcd import gcd_sta
    gcd_sta.main()

    manifest = 'build/gcd/job0/timing/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    manifest = 'build/gcd/job0/gcd.pkg.json'
    assert os.path.isfile(manifest)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_gcd_ihp130():
    from gcd import gcd_ihp130
    gcd_ihp130.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/signoff/drc/0/outputs/gcd.lyrdb')

    manifest = 'build/gcd/signoff/convert/0/outputs/gcd.pkg.json'
    chip = siliconcompiler.Chip('gcd')
    chip.read_manifest(manifest)
    # DRCs are density and fantom enclosure rules at the block pins
    assert chip.get('metric', 'drcs', step='drc', index='0') == 13
