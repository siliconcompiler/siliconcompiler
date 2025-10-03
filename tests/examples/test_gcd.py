import pytest

import os.path

from siliconcompiler import Project


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(600)
def test_py_gcd():
    from gcd import gcd
    gcd.main()

    manifest = 'build/gcd/job0/gcd.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history("job0")

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
    # Verify that final manifest was recorded.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')

    assert project.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                       step='synthesis', index='0') == ['reports/stat.json']

    # "No timescale set..."
    assert project.get('metric', 'warnings', step='elaborate', index='0') == 7

    # 2 ABC Warnings
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 2

    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 2

    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.ready
@pytest.mark.timeout(900)
def test_py_gcd_skywater():
    from gcd import gcd_skywater

    gcd_skywater.main()

    assert os.path.isfile('build/gcd/rtl2gds/write.gds/0/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/signoff/gcd.pkg.json')

    # # Verify that the build was LVS and DRC clean.
    # assert chip.get('metric', 'drcs', step='lvs', index='0') == 0
    # assert chip.get('metric', 'drcs', step='drc', index='0') == 0


@pytest.mark.eda
@pytest.mark.ready
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
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_gcd_ihp130():
    from gcd import gcd_ihp130
    gcd_ihp130.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/signoff/drc/0/outputs/gcd.lyrdb')

    # manifest = 'build/gcd/signoff/convert/0/outputs/gcd.pkg.json'
    # chip = siliconcompiler.Chip('gcd')
    # chip.read_manifest(manifest)
    # # DRCs are density and fantom enclosure rules at the block pins
    # assert chip.get('metric', 'drcs', step='drc', index='0') == 13


@pytest.mark.eda
@pytest.mark.ready
@pytest.mark.timeout(1200)
@pytest.mark.skip(reason="does not complete synthesis")
def test_py_gcd_hls():
    from gcd import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(600)
def test_py_gcd_chisel():
    from gcd import gcd_chisel
    gcd_chisel.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/GCD.gds')
