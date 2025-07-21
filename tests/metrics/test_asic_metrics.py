import pytest

from siliconcompiler.metrics import ASICMetricsSchema
from siliconcompiler.schema import Scope, PerNode


def test_keys():
    assert ASICMetricsSchema().allkeys() == set([
        ('tasktime',),
        ('warnings',),
        ('registers',),
        ('errors',),
        ('buffers',),
        ('holdwns',),
        ('cellarea',),
        ('holdskew',),
        ('utilization',),
        ('padcellarea',),
        ('nets',),
        ('averagepower',),
        ('unconstrained',),
        ('setuptns',),
        ('exetime',),
        ('wirelength',),
        ('macroarea',),
        ('holdpaths',),
        ('vias',),
        ('pins',),
        ('macros',),
        ('leakagepower',),
        ('setupskew',),
        ('overflow',),
        ('logicdepth',),
        ('stdcellarea',),
        ('irdrop',),
        ('setuppaths',),
        ('peakpower',),
        ('holdslack',),
        ('drcs',),
        ('fmax',),
        ('cells',),
        ('transistors',),
        ('memory',),
        ('inverters',),
        ('holdtns',),
        ('setupwns',),
        ('drvs',),
        ('totalarea',),
        ('setupslack',),
        ('totaltime',)
    ])


@pytest.mark.parametrize("key", ASICMetricsSchema().allkeys())
def test_key_params(key):
    param = ASICMetricsSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.REQUIRED
    assert param.get(field="scope") == Scope.JOB
