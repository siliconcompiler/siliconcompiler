import pytest

from siliconcompiler.schema import Scope
from siliconcompiler.schema_support.option import OptionSchema, SchedulerSchema


def test_keys():
    assert OptionSchema().allkeys() == set([
        ('builddir',),
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

# Tests use pytest for parametrization and assertions.
SCHEDULER_OPTION_KEYS = sorted(
    key
    for key in OptionSchema().allkeys()
    if key and key[0] == 'scheduler' and len(key) > 1
)


@pytest.mark.parametrize("key", SCHEDULER_OPTION_KEYS)
def test_scheduler_option_keys_have_global_scope(key):
    opt = OptionSchema()
    param = opt.get(*key, field=None)
    assert param.get(field="scope") == Scope.GLOBAL


def test_scheduler_schema_allkeys_match_option_schema():
    opt = OptionSchema()
    scheduler_schema = opt.scheduler
    option_scheduler_keys = {
        key[1:]
        for key in opt.allkeys()
        if key and key[0] == 'scheduler' and len(key) > 1
    }
    assert scheduler_schema.allkeys() == option_scheduler_keys


def test_scheduler_subschema_parameters_are_accessible():
    scheduler_schema = OptionSchema().scheduler
    for key in scheduler_schema.allkeys():
        param = scheduler_schema.get(*key, field=None)
        assert param is not None
        assert param.get(field="scope") == Scope.GLOBAL
