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


###########################
# OptionSchema Tests
###########################
def test_option_schema_simple_get_set():
    """Test simple setters and getters for OptionSchema."""

    option = OptionSchema()

    # remote
    option.set_remote(True)
    assert option.get_remote() is True

    # credentials
    option.set_credentials('/path/to/creds')
    assert option.get_credentials() == '/path/to/creds'

    # cachedir
    option.set_cachedir('/path/to/cache')
    assert option.get_cachedir() == '/path/to/cache'

    # flow
    option.set_flow('testflow')
    assert option.get_flow() == 'testflow'

    # builddir
    option.set_builddir('build_dir')
    assert option.get_builddir() == 'build_dir'

    # jobname
    option.set_jobname('testjob')
    assert option.get_jobname() == 'testjob'

    # clean
    option.set_clean(True)
    assert option.get_clean() is True

    # hash
    option.set_hash(True)
    assert option.get_hash() is True

    # nodisplay
    option.set_nodisplay(True)
    assert option.get_nodisplay() is True

    # jobincr
    option.set_jobincr(True)
    assert option.get_jobincr() is True

    # design
    option.set_design('testdesign')
    assert option.get_design() == 'testdesign'

    # nodashboard
    option.set_nodashboard(True)
    assert option.get_nodashboard() is True

    # env
    option.set_env('PDK_VAR', '/path/to/pdk')
    assert option.get_env('PDK_VAR') == '/path/to/pdk'


def test_option_schema_pernode():
    """Test PerNode.OPTIONAL setters and getters for OptionSchema."""
    step = 'syn'
    index = '0'

    option = OptionSchema()

    # nice
    option.set_nice(10)
    option.set_nice(5, step=step, index=index)
    assert option.get_nice() == 10
    assert option.get_nice(step=step, index=index) == 5

    # optmode
    option.set_optmode(3)
    option.set_optmode(1, step=step, index=index)
    assert option.get_optmode() == 3
    assert option.get_optmode(step=step, index=index) == 1

    # breakpoint
    option.set_breakpoint(True)
    option.set_breakpoint(False, step=step, index=index)
    assert option.get_breakpoint() is True
    assert option.get_breakpoint(step=step, index=index) is False

    # quiet
    option.set_quiet(True)
    option.set_quiet(False, step=step, index=index)
    assert option.get_quiet() is True
    assert option.get_quiet(step=step, index=index) is False

    # novercheck
    option.set_novercheck(True)
    option.set_novercheck(False, step=step, index=index)
    assert option.get_novercheck() is True
    assert option.get_novercheck(step=step, index=index) is False

    # track
    option.set_track(True)
    option.set_track(False, step=step, index=index)
    assert option.get_track() is True
    assert option.get_track(step=step, index=index) is False

    # continue
    option.set_continue(True)
    option.set_continue(False, step=step, index=index)
    assert option.get_continue() is True
    assert option.get_continue(step=step, index=index) is False

    # timeout
    option.set_timeout(3600.0)
    option.set_timeout(1800.0, step=step, index=index)
    assert option.get_timeout() == 3600.0
    assert option.get_timeout(step=step, index=index) == 1800.0


def test_option_schema_adders():
    """Test list-based adders for OptionSchema."""

    option = OptionSchema()

    # from
    option.add_from('import')
    option.add_from(['syn', 'place'])
    assert option.get_from() == ['import', 'syn', 'place']
    option.add_from('route', clobber=True)
    assert option.get_from() == ['route']

    # to
    option.add_to('syn')
    option.add_to(['place', 'route'])
    assert option.get_to() == ['syn', 'place', 'route']
    option.add_to('cts', clobber=True)
    assert option.get_to() == ['cts']

    # prune
    option.add_prune(('syn', '0'))
    option.add_prune([('place', '0'), ('route', '0')])
    assert option.get_prune() == [('syn', '0'), ('place', '0'), ('route', '0')]
    option.add_prune([('cts', '0')], clobber=True)
    assert option.get_prune() == [('cts', '0')]

    # alias
    option.add_alias(('a', 'b', 'c', 'd'))
    option.add_alias([('e', 'f', 'g', 'h')])
    assert option.get_alias() == [('a', 'b', 'c', 'd'), ('e', 'f', 'g', 'h')]
    option.add_alias((('i', 'j', 'k', 'l'),), clobber=True)
    assert option.get_alias() == [('i', 'j', 'k', 'l')]

    # fileset
    option.add_fileset('rtl')
    option.add_fileset(['constraints', 'gds'])
    assert option.get_fileset() == ['rtl', 'constraints', 'gds']
    option.add_fileset('netlist', clobber=True)
    assert option.get_fileset() == ['netlist']


###########################
# SchedulerSchema Tests
###########################

def test_scheduler_schema_pernode_set():
    """Test PerNode.OPTIONAL setters and getters for SchedulerSchema."""
    scheduler = OptionSchema().scheduler
    step = 'syn'
    index = '0'

    # name
    scheduler.set_name('slurm')
    scheduler.set_name('lsf', step=step, index=index)
    assert scheduler.get_name() == 'slurm'
    assert scheduler.get_name(step=step, index=index) == 'lsf'

    # cores
    scheduler.set_cores(48)
    scheduler.set_cores(24, step=step, index=index)
    assert scheduler.get_cores() == 48
    assert scheduler.get_cores(step=step, index=index) == 24

    # memory
    scheduler.set_memory(8000)
    scheduler.set_memory(4000, step=step, index=index)
    assert scheduler.get_memory() == 8000
    assert scheduler.get_memory(step=step, index=index) == 4000

    # queue
    scheduler.set_queue('night')
    scheduler.set_queue('day', step=step, index=index)
    assert scheduler.get_queue() == 'night'
    assert scheduler.get_queue(step=step, index=index) == 'day'

    # defer
    scheduler.set_defer('16:00')
    scheduler.set_defer('now+1h', step=step, index=index)
    assert scheduler.get_defer() == '16:00'
    assert scheduler.get_defer(step=step, index=index) == 'now+1h'


def test_scheduler_schema_adders():
    """Test list-based adders for SchedulerSchema."""
    scheduler = OptionSchema().scheduler
    step = 'syn'
    index = '0'

    # options
    scheduler.add_options('--pty')
    scheduler.add_options(['-N 1'], step=step, index=index)
    assert scheduler.get_options() == ['--pty']
    assert scheduler.get_options(step=step, index=index) == ['-N 1']
    scheduler.add_options(['-N 2'], step=step, index=index)
    assert scheduler.get_options(step=step, index=index) == ['-N 1', '-N 2']
    scheduler.add_options(['--new'], step=step, index=index, clobber=True)
    assert scheduler.get_options(step=step, index=index) == ['--new']

    # msgevent
    scheduler.add_msgevent('fail')
    scheduler.add_msgevent(['begin', 'end'], step=step, index=index)
    assert scheduler.get_msgevent() == ['fail']
    assert scheduler.get_msgevent(step=step, index=index) == ['begin', 'end']
    scheduler.add_msgevent('all', step=step, index=index, clobber=True)
    assert scheduler.get_msgevent() == ['fail']  # global shouldn't be clobbered
    assert scheduler.get_msgevent(step=step, index=index) == ['all']

    # msgcontact
    scheduler.add_msgcontact('test@example.com')
    scheduler.add_msgcontact(['foo@bar.com'], step=step, index=index)
    assert scheduler.get_msgcontact() == ['test@example.com']
    assert scheduler.get_msgcontact(step=step, index=index) == ['foo@bar.com']
    scheduler.add_msgcontact('another@email.com', step=step, index=index)
    assert scheduler.get_msgcontact(step=step, index=index) == ['foo@bar.com', 'another@email.com']
    scheduler.add_msgcontact(['new@email.com'], step=step, index=index, clobber=True)
    assert scheduler.get_msgcontact(step=step, index=index) == ['new@email.com']


def test_scheduler_schema_global():
    """Test global-only setters and getters for SchedulerSchema."""
    scheduler = OptionSchema().scheduler

    # maxnodes
    scheduler.set_maxnodes(4)
    assert scheduler.get_maxnodes() == 4

    # maxthreads
    scheduler.set_maxthreads(8)
    assert scheduler.get_maxthreads() == 8
