import pytest
import re


@pytest.mark.eda
@pytest.mark.quick
def test_gcd_infer_diesize(gcd_chip_dir, monkeypatch):
    '''Test inferring diesize from density/aspectratio/margin arguments
    '''

    gcd_chip, rundir = gcd_chip_dir
    monkeypatch.chdir(rundir)

    # Parse die area from resulting DEF. We could pull this from schema, but we
    # want to make entire floorplan flow works.
    post_floorplan_def = gcd_chip.find_result('def', step='floorplan.init')
    with open(post_floorplan_def, 'r') as f:
        diearea = None
        for line in f:
            regex = r'DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;'
            match = re.match(regex, line)
            if match is None:
                continue
            diearea = match.group(1, 2, 3, 4)
            break

    assert diearea == ('0', '0', '200260', '201600')
