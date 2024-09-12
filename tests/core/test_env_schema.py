import siliconcompiler
import os
import pytest
import multiprocessing

from core.tools.dummy import environment
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.skipif(
    multiprocessing.get_start_method() != 'fork',
    reason="Mocking _runtask() does not work with the multiprocessing 'spawn' start method"
)
def test_env(monkeypatch):
    chip = siliconcompiler.Chip('test')
    # File doesn't need to resolve, just need to put something in the schema so
    # we don't fail the initial static check_manifest().
    chip.input('fake.v')
    chip.use(freepdk45_demo)
    chip.set('option', 'to', ['import'])
    flow = chip.get('option', 'flow')
    chip.modules.clear()
    chip.set('flowgraph', flow, 'import', '0', 'tool', 'dummy')
    chip.set('flowgraph', flow, 'import', '0', 'task', 'environment')
    chip.set('flowgraph', flow, 'import', '0', 'taskmodule', environment.__name__)

    # Set env
    chip.set('option', 'env', 'TEST', 'hello')
    chip.set('tool', 'dummy', 'task', 'environment', 'var', 'env', 'TEST')
    chip.set('tool', 'dummy', 'task', 'environment', 'var', 'assert', 'hello')

    chip.run()

    # Ensure env variable is set in current process
    assert 'TEST' not in os.environ
