import siliconcompiler
import os
import pytest
import multiprocessing

@pytest.mark.skipif(
    multiprocessing.get_start_method() != 'fork',
    reason="Mocking _runtask() does not work with the multiprocessing 'spawn' start method"
)
def test_env(monkeypatch):
    chip = siliconcompiler.Chip('test')
    # File doesn't need to resolve, just need to put something in the schema so
    # we don't fail the initial static check_manifest().
    chip.add('input', 'rtl', 'verilog', 'fake.v')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'steplist', 'import')

    # Set env
    chip.set('option', 'env', 'TEST', 'hello')

    # Mock _runtask() so we can test without tools
    def fake_runtask(chip, step, index, status):
        chip._init_logger(step, index, in_run=True)

        # Ensure env variable is propagated to tasks
        assert os.environ['TEST'] == 'hello'

        # Logic to make sure chip.run() registers task as success

        chip.set('flowgraph', 'asicflow', step, index, 'status', siliconcompiler.TaskStatus.SUCCESS)
        outdir = chip._getworkdir(step=step, index=index)
        chip.write_manifest(os.path.join(outdir, 'outputs', f"{chip.get('design')}.pkg.json"))

    monkeypatch.setattr(siliconcompiler.Chip, '_runtask', fake_runtask)

    chip.run()

    # Ensure env variable is set in current process
    assert os.environ['TEST'] == 'hello'
