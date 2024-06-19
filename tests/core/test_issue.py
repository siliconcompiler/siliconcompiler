import siliconcompiler

import pytest
import glob


@pytest.mark.quick
@pytest.mark.eda
@pytest.mark.timeout(300)
def test_automatic_issue(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    gcd_chip.set('option', 'to', 'cts')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    assert len(glob.glob(f'{gcd_chip._getworkdir()}/sc_issue*.tar.gz')) == 1

    with open(f'{gcd_chip._getworkdir(step="place", index="0")}/sc_place0.log') as f:
        text = f.read()
        assert "Collecting input sources" not in text
        assert "Copying " not in text
