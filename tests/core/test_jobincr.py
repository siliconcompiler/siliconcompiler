import siliconcompiler

def test_jobincr():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.set('option', 'flow', 'test')
    chip.node(flow, 'import', 'echo')

    chip.set('option', 'jobincr', True)

    chip.run()
    assert chip._getworkdir().endswith('build/test/job0')

    chip.run()
    assert chip._getworkdir().endswith('build/test/job1')
