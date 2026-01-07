# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad import metrics
from siliconcompiler.utils.paths import workdir


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_images(asic_gcd):
    for task in APRTask.find_task(asic_gcd):
        task.set('var', 'ord_enable_images', True)

    assert asic_gcd.run()

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
                os.path.join(workdir(asic_gcd, step=step, index='0'),
                             'reports',
                             'images')):
            count += len(files)
            all_files.update([os.path.relpath(
                os.path.join(dirpath, f),
                workdir(asic_gcd, step=step, index='0')) for f in files])

        assert images_count[step] == count, f'{step} images do not match: ' \
                                            f'{images_count[step]} == {count}: {all_files}'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_metrics_task(asic_gcd):
    flow = ASICFlow("testflow")
    flow.node("metrics", metrics.MetricsTask())
    flow.edge('floorplan.init', 'metrics')

    asic_gcd.set_flow(flow)
    asic_gcd.set('option', 'to', 'metrics')
    assert asic_gcd.run()

    assert asic_gcd.history("job0").get('metric', 'cellarea', step='metrics', index='0') is not \
        None
    assert asic_gcd.history("job0").get('metric', 'totalarea', step='metrics', index='0') is not \
        None


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_pin_placement(asic_heartbeat):
    clk = asic_heartbeat.constraint.pin.make_pinconstraint("clk")
    clk.set_layer("metal4")
    clk.set_order(1)
    clk.set_side("top")
    nreset = asic_heartbeat.constraint.pin.make_pinconstraint("nreset")
    nreset.set_layer("metal4")
    nreset.set_order(2)
    nreset.set_side("top")
    out = asic_heartbeat.constraint.pin.make_pinconstraint("out")
    out.set_layer("metal2")
    out.set_order(1)
    out.set_side("bottom")

    asic_heartbeat.option.add_to("floorplan.init")

    job = asic_heartbeat.run()
    assert job
    report = job.find_result(step='floorplan.init', directory=".", filename="floorplan.init.log")
    with open(report, 'r') as f:
        log = f.read()
    assert log.count("Pin clk placed at") == 1
    assert log.count("Pin nreset placed at") == 1
    assert log.count("Pin out placed at") == 1
