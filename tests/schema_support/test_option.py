import pytest

from siliconcompiler.schema import Scope
from siliconcompiler.schema_support.option import OptionSchema, SchedulerSchema


def test_keys():
    assert OptionSchema().allkeys() == set([
        ('builddir',),
        ('strict',),
        ('loglevel',),
        ('flow',),
        ('prune',),
        ('from',),
        ('jobincr',),
        ('scheduler', 'maxthreads'),
        ('scheduler', 'maxnodes'),
        ('nodisplay',),
        ('scheduler', 'memory'),
        ('credentials',),
        ('novercheck',),
        ('nodashboard',),
        ('jobname',),
        ('remote',),
        ('env', 'default'),
        ('timeout',),
        ('hash',),
        ('breakpoint',),
        ('scheduler', 'options'),
        ('track',), ('continue',),
        ('scheduler', 'name'),
        ('fileset',),
        ('nice',),
        ('design',),
        ('scheduler', 'queue'),
        ('scheduler', 'msgcontact'),
        ('optmode',),
        ('scheduler', 'defer'),
        ('scheduler', 'cores'),
        ('clean',),
        ('alias',),
        ('to',),
        ('cachedir',),
        ('scheduler', 'msgevent'),
        ('quiet',)
    ])


@pytest.mark.parametrize("key", [
    key for key in OptionSchema().allkeys() if key not in (
        ('to',),
        ('from',),
        ('prune',),
        ('breakpoint',),
    )])
def test_key_params_global(key):
    param = OptionSchema().get(*key, field=None)
    assert param.get(field="scope") == Scope.GLOBAL


@pytest.mark.parametrize("key", [
    key for key in OptionSchema().allkeys() if key in (
        ('to',),
        ('from',),
        ('prune',),
        ('breakpoint',),
    )])
def test_key_params_job(key):
    param = OptionSchema().get(*key, field=None)
    assert param.get(field="scope") == Scope.JOB


def test_scheduler():
    opt = OptionSchema()
    assert isinstance(opt.scheduler, SchedulerSchema)
    assert opt.get("scheduler", field="schema") is opt.scheduler
