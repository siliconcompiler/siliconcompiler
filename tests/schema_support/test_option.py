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


# Note: Tests leverage pytest, consistent with the project's use of pytest.


def _flatten_list(value):
    if value is None:
        return []
    if not isinstance(value, list):
        return [value]
    result = []
    for item in value:
        if isinstance(item, list):
            result.extend(_flatten_list(item))
        else:
            result.append(item)
    return result


def test_option_schema_remote_roundtrip():
    schema = OptionSchema()
    schema.set_remote(True)
    assert schema.get_remote() is True
    schema.set_remote(False)
    assert schema.get_remote() is False


def test_option_schema_add_from_behavior():
    schema = OptionSchema()
    schema.add_from('import')
    schema.add_from(['syn', 'route'])
    result = _flatten_list(schema.get_from())
    assert result == ['import', 'syn', 'route']


def test_option_schema_add_from_clobber_replaces():
    schema = OptionSchema()
    schema.add_from(['import', 'syn'])
    schema.add_from(['final'], clobber=True)
    assert _flatten_list(schema.get_from()) == ['final']


def test_scheduler_schema_options_accumulate_and_clobber():
    scheduler = SchedulerSchema()
    scheduler.add_options(['--pty'])
    scheduler.add_options('--exclusive')
    options = _flatten_list(scheduler.get_options())
    assert options == ['--pty', '--exclusive']
    scheduler.add_options(['--fresh'], clobber=True)
    assert _flatten_list(scheduler.get_options()) == ['--fresh']


def test_scheduler_schema_step_specific_queue():
    scheduler = SchedulerSchema()
    scheduler.set_queue('default')
    scheduler.set_queue('night', step='place', index='0')
    assert scheduler.get_queue() == 'default'
    assert scheduler.get_queue(step='place', index='0') == 'night'


def test_option_schema_env_roundtrip():
    schema = OptionSchema()
    schema.set_env('PDK_HOME', '/path/to/pdk')
    assert schema.get_env('PDK_HOME') == '/path/to/pdk'


def test_option_schema_add_prune_handles_clobber():
    schema = OptionSchema()
    schema.add_prune(('syn', '0'))
    schema.add_prune([('place', '1')])
    prune_values = schema.get_prune()
    assert prune_values is not None
    assert ('syn', '0') in prune_values
    assert ('place', '1') in prune_values
    schema.add_prune([('final', '2')], clobber=True)
    assert schema.get_prune() == [('final', '2')]


def test_scheduler_property_shared_instance_updates_parent():
    option = OptionSchema()
    scheduler = option.scheduler
    scheduler.set_maxthreads(8)
    assert option.scheduler.get_maxthreads() == 8


def test_option_schema_nice_values_scoped():
    schema = OptionSchema()
    schema.set_nice(3)
    assert schema.get_nice() == 3
    schema.set_nice(5, step='syn', index='0')
    assert schema.get_nice(step='syn', index='0') == 5
    assert schema.get_nice() == 3


def test_scheduler_schema_add_msgcontact_behavior():
    scheduler = SchedulerSchema()
    scheduler.add_msgcontact(['user@example.com'])
    scheduler.add_msgcontact('ops@example.com')
    contacts = _flatten_list(scheduler.get_msgcontact())
    assert 'user@example.com' in contacts
    assert 'ops@example.com' in contacts
    scheduler.add_msgcontact(['fresh@example.com'], clobber=True)
    assert _flatten_list(scheduler.get_msgcontact()) == ['fresh@example.com']