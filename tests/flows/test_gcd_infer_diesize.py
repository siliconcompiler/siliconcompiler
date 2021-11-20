import pytest
import re

@pytest.mark.eda
def test_gcd_infer_diesize(gcd_chip):
    '''Test inferring diesize from density/aspectratio/margin arguments
    '''

    gcd_chip.set('asic', 'diearea', [])
    gcd_chip.set('asic', 'corearea', [])

    gcd_chip.add('steplist', 'import')
    gcd_chip.add('steplist', 'syn')
    gcd_chip.add('steplist', 'synmin')
    gcd_chip.add('steplist', 'floorplan')

    gcd_chip.run()

    # Parse die area from resulting DEF. We could pull this from schema, but we
    # want to make entire floorplan flow works.
    post_floorplan_def = gcd_chip.find_result('def', step='floorplan')
    with open(post_floorplan_def, 'r') as f:
        diearea = None
        for line in f:
            regex = r'DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \) ;'
            match = re.match(regex, line)
            if match is None:
                continue
            diearea = match.group(1, 2, 3, 4)
            break

    assert diearea == ('0', '0', '136400', '136400')

if __name__ == '__main__':
    from tests.fixtures import gcd_chip
    test_gcd_infer_diesize(gcd_chip())
