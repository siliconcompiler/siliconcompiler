import siliconcompiler
from siliconcompiler.tools.builtin import nop
import sys


def test_track():
    chip = siliconcompiler.Chip('test')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.set('option', 'track', True)

    chip.run()

    for key in chip.getkeys('record'):
        if key in ('remoteid', 'publickey', 'toolversion', 'toolpath', 'toolargs',
                   'status', 'inputnode'):
            # won't get set based on run
            continue

        if sys.platform != 'linux':
            # won't get set on non-linux systems
            if key in ('distro', ):
                continue
        assert chip.get('record', key, step='import', index='0'), f"no record for {key}"
