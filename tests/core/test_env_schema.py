import siliconcompiler
import os
import pytest
import multiprocessing

@pytest.mark.skipif(
    multiprocessing.get_start_method() != 'fork',
    reason="Mocking _runtask() does not work with the multiprocessing 'spawn' start method"
)
def test_env(monkeypatch):
    chip = siliconcompiler.Chip()
    chip.set('design', 'test')
    chip.target('asicflow_freepdk45')
    chip.set('steplist', 'import')

    # Set env
    chip.set('env', 'TEST', 'hello')

    def fake_runtask(chip, step, index, active, error):
        # Ensure env variable is propagated to tasks
        assert os.environ['TEST'] == 'hello'

        # Logic to make sure chip.run() registers task as success
        outdir = chip._getworkdir(step=step, index=index)
        chip.write_manifest(os.path.join(outdir, 'outputs', f"{chip.get('design')}.pkg.json"))
        active[step + str(index)] = 0
        error[step + str(index)] = 0

    # Mock _runtask() so we can test without tools
    monkeypatch.setattr(siliconcompiler.Chip, '_runtask', fake_runtask)

    chip.run()

    # Ensure env variable is set in current process
    assert os.environ['TEST'] == 'hello'
