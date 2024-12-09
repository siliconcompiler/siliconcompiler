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
        if key in ('remoteid', 'publickey', 'toolversion', 'toolpath', 'toolexitcode', 'toolargs',
                   'status', 'inputnode'):
            # won't get set based on run
            continue

        if sys.platform != 'linux':
            # won't get set on non-linux systems
            if key in ('distro', ):
                continue

        step, index = 'import', '0'
        if chip.get('record', key, field='pernode') == 'never':
            step, index = None, None
        assert chip.get('record', key, step=step, index=index), f"no record for {key}"


def test_track_packages(monkeypatch):
    import pip._internal.vcs.subversion
    monkeypatch.setattr(pip._internal.vcs.subversion, 'is_console_interactive', (lambda: False))

    import pip._internal.operations.freeze

    def mock():
        return ["sc==1", "test==2"]

    monkeypatch.setattr(pip._internal.operations.freeze, 'freeze', mock)

    chip = siliconcompiler.Chip('test')
    flow = siliconcompiler.Flow('test')
    flow.node('test', 'test', nop)

    chip.use(flow)

    chip.set('option', 'flow', 'test')
    chip.run()

    assert len(chip.get('record', 'pythonpackage')) == 2
    assert chip.get('record', 'pythonpackage') == ["sc==1", "test==2"]
