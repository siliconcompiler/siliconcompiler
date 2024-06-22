import siliconcompiler
from siliconcompiler.tools.builtin import nop


def test_track():
    chip = siliconcompiler.Chip('test')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.set('option', 'mode', 'asic')
    chip.set('option', 'track', True)

    chip.run()

    for key in chip.getkeys('record'):
        if key in ('remoteid', 'publickey', 'toolversion', 'toolpath', 'toolargs'):
            continue
        assert chip.get('record', key, step='import', index='0'), f"no record for {key}"
