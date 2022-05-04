# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

import pytest

def test_summary(datadir):

    chip = siliconcompiler.Chip('test')
    manifest = os.path.join(datadir, 'gcd.pkg.json')

    chip.read_manifest(manifest)

    chip.summary()

def test_steplist(datadir, capfd):
    with capfd.disabled():
        chip = siliconcompiler.Chip('test')
        manifest = os.path.join(datadir, 'gcd.pkg.json')

        chip.read_manifest(manifest)
        chip.set('option','steplist', ['syn'])

    chip.summary()
    stdout, _ = capfd.readouterr()

    assert 'import0' not in stdout
    assert 'syn0' in stdout

def test_parallel_path(capfd):
    with capfd.disabled():
        chip = siliconcompiler.Chip('test')
        chip.set('design', 'test')

        flow = 'test'
        chip.set('option','flow', flow)
        chip.node(flow, 'import', 'nop')
        chip.node(flow, 'ctsmin', 'minimum')

        chip.set('flowgraph', 'import', '0', 'status', siliconcompiler.TaskStatus.SUCCESS)
        chip.set('flowgraph', 'ctsmin', '0', 'status', siliconcompiler.TaskStatus.SUCCESS)
        chip.set('flowgraph', 'ctsmin', '0', 'select', ('cts', '1'))

        for i in ('0', '1', '2'):
            chip.node(flow, 'place', 'openroad', index=i)
            chip.node(flow, 'cts', 'openroad', index=i)

            chip.set('flowgraph', 'place', i, 'status', siliconcompiler.TaskStatus.SUCCESS)
            chip.set('flowgraph', 'cts', i, 'status', siliconcompiler.TaskStatus.SUCCESS)

            chip.edge(flow, 'place', 'cts', tail_index=i, head_index=i)
            chip.edge(flow, 'cts', 'ctsmin', tail_index=i)
            chip.edge(flow, 'import', 'place', head_index=i)

            chip.set('flowgraph', 'place', i, 'select', ('import', '0'))
            chip.set('flowgraph', 'cts', i, 'select', ('place', i))

    chip.write_flowgraph('test_graph.png')

    chip.summary()
    stdout, _ = capfd.readouterr()
    print(stdout)
    assert 'place1' in stdout
    assert 'cts1' in stdout
    assert 'place0' not in stdout
    assert 'cts0' not in stdout
    assert 'place2' not in stdout
    assert 'cts2' not in stdout

@pytest.mark.eda
def test_steplist_repeat(gcd_chip, capfd):
    '''Regression test for #458.'''
    with capfd.disabled():
        gcd_chip.set('option', 'steplist', ['import', 'syn', 'floorplan'])
        gcd_chip.run()
        gcd_chip.set('option', 'steplist', ['syn'])
        gcd_chip.run()

    gcd_chip.summary()
    stdout, _ = capfd.readouterr()
    print(stdout)

    assert 'import0' not in stdout
    assert 'syn0' in stdout
    assert 'floorplan0' not in stdout

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_summary(datadir(__file__))
