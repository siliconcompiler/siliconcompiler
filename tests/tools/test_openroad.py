# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

from siliconcompiler.tools.openroad import init_floorplan
from siliconcompiler.tools.openroad import metrics

from siliconcompiler.tools.builtin import nop
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import SchedulerNode


def _setup_fifo(scroot):
    datadir = os.path.join(scroot, 'tests', 'data')
    netlist = os.path.join(datadir, 'oh_fifo_sync_freepdk45.vg')

    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)

    chip.input(netlist)
    chip.set('option', 'quiet', True)
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])

    # load tech
    chip.use(freepdk45_demo)

    # set up tool for floorplan
    flow = 'floorplan'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'floorplan', init_floorplan)
    chip.edge(flow, 'import', 'floorplan')
    chip.set('option', 'flow', flow)

    return chip


@pytest.mark.eda
@pytest.mark.quick
def test_openroad(scroot):
    chip = _setup_fifo(scroot)

    assert chip.run()

    # check that compilation succeeded
    assert chip.find_result('def', step='floorplan') is not None

    # check that metrics were recorded
    assert chip.get('metric', 'cellarea', step='floorplan', index='0') is not None
    assert chip.get('tool', 'openroad', 'task', 'init_floorplan', 'report', 'cellarea',
                    step='floorplan', index='0') == ['reports/metrics.json']


@pytest.mark.eda
@pytest.mark.quick
def test_openroad_screenshot(scroot):
    chip = _setup_fifo(scroot)
    chip.set('tool', 'openroad', 'task', 'init_floorplan', 'var', 'ord_enable_images', 'true')

    assert chip.run()

    # check that compilation succeeded
    assert chip.find_result('def', step='floorplan') is not None
    assert chip.find_result('odb', step='floorplan') is not None

    assert os.path.exists(os.path.join(chip.getworkdir(step='floorplan', index='0'),
                                       'reports',
                                       'images',
                                       f'{chip.design}.png'))


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_images(gcd_chip):
    for task in (
            'init_floorplan',
            'detailed_placement',
            'clock_tree_synthesis',
            'detailed_route',
            'write_data'):
        gcd_chip.set('tool', 'openroad', 'task', task, 'var', 'ord_enable_images', 'true')

    assert gcd_chip.run()

    images_count = {
        'floorplan.init': 2,
        'place.detailed': 6,
        'cts.clock_tree_synthesis': 10,
        'route.detailed': 12,
        'write.views': 28,
    }

    for step in images_count.keys():
        count = 0
        all_files = set()
        for dirpath, _, files in os.walk(
                os.path.join(gcd_chip.getworkdir(step=step, index='0'),
                             'reports',
                             'images')):
            count += len(files)
            all_files.update([os.path.relpath(
                os.path.join(dirpath, f),
                gcd_chip.getworkdir(step=step, index='0')) for f in files])

        assert images_count[step] == count, f'{step} images do not match: ' \
                                            f'{images_count[step]} == {count}: {all_files}'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_metrics_task(gcd_chip):
    gcd_chip.node('asicflow', 'metrics', metrics)
    gcd_chip.edge('asicflow', 'floorplan.init', 'metrics')
    gcd_chip.set('option', 'to', 'metrics')
    assert gcd_chip.run()

    assert gcd_chip.get('metric', 'cellarea', step='metrics', index='0') is not None
    assert gcd_chip.get('metric', 'totalarea', step='metrics', index='0') is not None


def test_library_selection():
    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)

    lib0 = siliconcompiler.Library('main_lib0')
    lib1 = siliconcompiler.Library('main_lib1')
    lib1.add('option', 'var', 'openroad_scan_chain_cells', 'test0')
    lib1.add('option', 'var', 'openroad_scan_chain_cells', 'test1')

    chip.use(lib0)
    chip.use(lib1)

    chip.add('asic', 'logiclib', 'main_lib0')
    chip.add('asic', 'logiclib', 'main_lib1')

    flow = 'init_floorplan'
    chip.node(flow, 'import', init_floorplan)
    chip.set('option', 'flow', flow)

    SchedulerNode(chip, 'import', '0').setup()

    assert set(chip.get('tool', 'openroad', 'task', 'init_floorplan', 'var', 'scan_chain_cells',
                        step='import', index='0')) == set(['test0', 'test1'])


def test_library_selection_user():
    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)

    lib0 = siliconcompiler.Library('main_lib0')
    lib1 = siliconcompiler.Library('main_lib1')
    lib1.add('option', 'var', 'openroad_scan_chain_cells', 'test0')
    lib1.add('option', 'var', 'openroad_scan_chain_cells', 'test1')

    chip.add('option', 'var', 'openroad_scan_chain_cells', 'user0')
    chip.add('option', 'var', 'openroad_scan_chain_cells', 'user1')

    chip.use(lib0)
    chip.use(lib1)

    chip.add('asic', 'logiclib', 'main_lib0')
    chip.add('asic', 'logiclib', 'main_lib1')

    flow = 'init_floorplan'
    chip.node(flow, 'import', init_floorplan)
    chip.set('option', 'flow', flow)

    SchedulerNode(chip, 'import', '0').setup()

    assert set(chip.get('tool', 'openroad', 'task', 'init_floorplan', 'var', 'scan_chain_cells',
                        step='import', index='0')) == set(['user0', 'user1'])
