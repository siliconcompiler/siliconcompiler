import pytest

from siliconcompiler.metrics import FPGAMetricsSchema
from siliconcompiler.schema import Scope, PerNode


def test_keys():
    assert FPGAMetricsSchema().allkeys() == set([
        ('holdskew',),
        ('fmax',),
        ('unconstrained',),
        ('holdslack',),
        ('exetime',),
        ('pins',),
        ('dsps',),
        ('setupslack',),
        ('registers',),
        ('overflow',),
        ('tasktime',),
        ('macros',),
        ('peakpower',),
        ('holdtns',),
        ('holdwns',),
        ('cells',),
        ('errors',),
        ('logicdepth',),
        ('luts',),
        ('utilization',),
        ('setuptns',),
        ('wirelength',),
        ('brams',),
        ('setupwns',),
        ('totaltime',),
        ('holdpaths',),
        ('warnings',),
        ('memory',),
        ('setupskew',),
        ('setuppaths',),
        ('nets',),
        ('averagepower',),
        ('leakagepower',)
    ])


@pytest.mark.parametrize("key", FPGAMetricsSchema().allkeys())
def test_key_params(key):
    param = FPGAMetricsSchema().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.REQUIRED
    assert param.get(field="scope") == Scope.JOB
