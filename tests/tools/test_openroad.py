# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad import metrics
from siliconcompiler.utils.paths import workdir
from siliconcompiler.tools import get_task


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_images(asic_gcd):
    for task in get_task(asic_gcd, filter=APRTask):
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
    class Flow(ASICFlow):
        def __init__(self):
            super().__init__()
            # Hack
            self._NamedSchema__name = None
            self.set_name("testflow")

            self.node("metrics", metrics.MetricsTask())
            self.edge('floorplan.init', 'metrics')

    asic_gcd.set_flow(Flow())
    asic_gcd.set('option', 'to', 'metrics')
    assert asic_gcd.run()

    assert asic_gcd.history("job0").get('metric', 'cellarea', step='metrics', index='0') is not \
        None
    assert asic_gcd.history("job0").get('metric', 'totalarea', step='metrics', index='0') is not \
        None
