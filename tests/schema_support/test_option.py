import pytest

from unittest.mock import patch

from siliconcompiler.schema import Scope
from siliconcompiler.schema_support.option import OptionSchema, SchedulerSchema
from siliconcompiler.project import Project


def test_keys():
    assert OptionSchema().allkeys() == set([
        ('autoissue',),
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
def test_remote():
    option = OptionSchema()
    option.set_remote(True)
    assert option.get_remote() is True


def test_credentials():
    option = OptionSchema()
    option.set_credentials('/path/to/creds')
    assert option.get_credentials() == '/path/to/creds'


def test_cachedir():
    option = OptionSchema()
    option.set_cachedir('/path/to/cache')
    assert option.get_cachedir() == '/path/to/cache'


def test_flow():
    option = OptionSchema()
    option.set_flow('testflow')
    assert option.get_flow() == 'testflow'


def test_builddir():
    option = OptionSchema()
    option.set_builddir('build_dir')
    assert option.get_builddir() == 'build_dir'


def test_jobname():
    option = OptionSchema()
    option.set_jobname('testjob')
    assert option.get_jobname() == 'testjob'


def test_clean():
    option = OptionSchema()
    assert option.get_clean() is False
    option.set_clean(True)
    assert option.get_clean() is True


def test_hash():
    option = OptionSchema()
    assert option.get_hash() is False
    option.set_hash(True)
    assert option.get_hash() is True


def test_nodisplay():
    option = OptionSchema()
    assert option.get_nodisplay() is False
    option.set_nodisplay(True)
    assert option.get_nodisplay() is True


def test_jobincr():
    option = OptionSchema()
    assert option.get_jobincr() is False
    option.set_jobincr(True)
    assert option.get_jobincr() is True


def test_design():
    option = OptionSchema()
    option.set_design('testdesign')
    assert option.get_design() == 'testdesign'


def test_nodashboard():
    option = OptionSchema()
    assert option.get_nodashboard() is False
    option.set_nodashboard(True)
    assert option.get_nodashboard() is True


def test_autoissue():
    option = OptionSchema()
    assert option.get_autoissue() is False
    option.set_autoissue(True)
    assert option.get_autoissue() is True


def test_nodashboard_via_callback():
    with patch("siliconcompiler.project.Project._Project__init_dashboard") as init:
        proj = Project()
        init.reset_mock()
        proj.option.set_nodashboard(True)
        init.assert_called_once()


def test_env():
    option = OptionSchema()
    option.set_env('PDK_VAR', '/path/to/pdk')
    assert option.get_env('PDK_VAR') == '/path/to/pdk'


def test_nice():
    option = OptionSchema()
    option.set_nice(10)
    option.set_nice(5, step="syn", index=1)
    assert option.get_nice() == 10
    assert option.get_nice(step="syn", index=1) == 5


def test_optmode():
    option = OptionSchema()
    option.set_optmode(3)
    option.set_optmode(1, step="syn", index=1)
    assert option.get_optmode() == 3
    assert option.get_optmode(step="syn", index=1) == 1


def test_breakpoint():
    option = OptionSchema()
    option.set_breakpoint(True)
    option.set_breakpoint(False, step="syn", index=1)
    assert option.get_breakpoint() is True
    assert option.get_breakpoint(step="syn", index=1) is False


def test_quiet():
    option = OptionSchema()
    option.set_quiet(True)
    option.set_quiet(False, step="syn", index=1)
    assert option.get_quiet() is True
    assert option.get_quiet(step="syn", index=1) is False


def test_novercheck():
    option = OptionSchema()
    option.set_novercheck(True)
    option.set_novercheck(False, step="syn", index=1)
    assert option.get_novercheck() is True
    assert option.get_novercheck(step="syn", index=1) is False


def test_track():
    option = OptionSchema()
    option.set_track(True)
    option.set_track(False, step="syn", index=1)
    assert option.get_track() is True
    assert option.get_track(step="syn", index=1) is False


def test_continue():
    option = OptionSchema()
    option.set_continue(True)
    option.set_continue(False, step="syn", index=1)
    assert option.get_continue() is True
    assert option.get_continue(step="syn", index=1) is False


def test_timeout():
    option = OptionSchema()
    option.set_timeout(3600.0)
    option.set_timeout(1800.0, step="syn", index=1)
    assert option.get_timeout() == 3600.0
    assert option.get_timeout(step="syn", index=1) == 1800.0


def test_from():
    option = OptionSchema()
    option.add_from('import')
    option.add_from(['syn', 'place'])
    assert option.get_from() == ['import', 'syn', 'place']
    option.add_from('route', clobber=True)
    assert option.get_from() == ['route']


def test_to():
    option = OptionSchema()
    option.add_to('syn')
    option.add_to(['place', 'route'])
    assert option.get_to() == ['syn', 'place', 'route']
    option.add_to('cts', clobber=True)
    assert option.get_to() == ['cts']


def test_prune():
    option = OptionSchema()
    option.add_prune(('syn', '0'))
    option.add_prune([('place', '0'), ('route', '0')])
    assert option.get_prune() == [('syn', '0'), ('place', '0'), ('route', '0')]
    option.add_prune([('cts', '0')], clobber=True)
    assert option.get_prune() == [('cts', '0')]


def test_alias():
    option = OptionSchema()
    option.add_alias(('a', 'b', 'c', 'd'))
    option.add_alias([('e', 'f', 'g', 'h')])
    assert option.get_alias() == [('a', 'b', 'c', 'd'), ('e', 'f', 'g', 'h')]
    option.add_alias((('i', 'j', 'k', 'l'),), clobber=True)
    assert option.get_alias() == [('i', 'j', 'k', 'l')]


def test_fileset():
    option = OptionSchema()
    option.add_fileset('rtl')
    option.add_fileset(['constraints', 'gds'])
    assert option.get_fileset() == ['rtl', 'constraints', 'gds']
    option.add_fileset('netlist', clobber=True)
    assert option.get_fileset() == ['netlist']


def test_callbacks():
    class Callback:
        calls_nodash = 0
        calls_track = 0

        @staticmethod
        def nodashboard():
            Callback.calls_nodash += 1

        @staticmethod
        def track():
            Callback.calls_track += 1

    option = OptionSchema()
    assert option._OptionSchema__callbacks == {}

    option._add_callback("nodashboard", Callback.nodashboard)
    option._add_callback("track", Callback.track)

    option.set_nodashboard(True)
    option.set_nodashboard(False)
    assert Callback.calls_nodash == 2
    assert Callback.calls_track == 0

    option.set_track(True)
    assert Callback.calls_nodash == 2
    assert Callback.calls_track == 1


def test_callbacks_invalid():
    with pytest.raises(KeyError, match=r"^'invalid is not supported for callbacks'$"):
        OptionSchema()._add_callback("invalid", None)


###########################
# SchedulerSchema Tests
###########################
def test_name():
    scheduler = OptionSchema().scheduler
    scheduler.set_name('slurm')
    scheduler.set_name('lsf', step="syn", index=1)
    assert scheduler.get_name() == 'slurm'
    assert scheduler.get_name(step="syn", index=1) == 'lsf'


def test_cores():
    scheduler = OptionSchema().scheduler
    scheduler.set_cores(48)
    scheduler.set_cores(24, step="syn", index=1)
    assert scheduler.get_cores() == 48
    assert scheduler.get_cores(step="syn", index=1) == 24


def test_memory():
    scheduler = OptionSchema().scheduler
    scheduler.set_memory(8000)
    scheduler.set_memory(4000, step="syn", index=1)
    assert scheduler.get_memory() == 8000
    assert scheduler.get_memory(step="syn", index=1) == 4000


def test_queue():
    scheduler = OptionSchema().scheduler
    scheduler.set_queue('night')
    scheduler.set_queue('day', step="syn", index=1)
    assert scheduler.get_queue() == 'night'
    assert scheduler.get_queue(step="syn", index=1) == 'day'


def test_defer():
    scheduler = OptionSchema().scheduler
    scheduler.set_defer('16:00')
    scheduler.set_defer('now+1h', step="syn", index=1)
    assert scheduler.get_defer() == '16:00'
    assert scheduler.get_defer(step="syn", index=1) == 'now+1h'


def test_options():
    scheduler = OptionSchema().scheduler
    scheduler.add_options('--pty')
    scheduler.add_options(['-N 1'], step="syn", index=1)
    assert scheduler.get_options() == ['--pty']
    assert scheduler.get_options(step="syn", index=1) == ['-N 1']
    scheduler.add_options(['-N 2'], step="syn", index=1)
    assert scheduler.get_options(step="syn", index=1) == ['-N 1', '-N 2']
    scheduler.add_options(['--new'], step="syn", index=1, clobber=True)
    assert scheduler.get_options(step="syn", index=1) == ['--new']


def test_msgevent():
    scheduler = OptionSchema().scheduler
    scheduler.add_msgevent('fail')
    scheduler.add_msgevent(['begin', 'end'], step="syn", index=1)
    assert scheduler.get_msgevent() == ['fail']
    assert scheduler.get_msgevent(step="syn", index=1) == ['begin', 'end']
    scheduler.add_msgevent('all', step="syn", index=1, clobber=True)
    assert scheduler.get_msgevent() == ['fail']  # global shouldn't be clobbered
    assert scheduler.get_msgevent(step="syn", index=1) == ['all']


def test_msgcontact():
    scheduler = OptionSchema().scheduler
    scheduler.add_msgcontact('test@example.com')
    scheduler.add_msgcontact(['foo@bar.com'], step="syn", index=1)
    assert scheduler.get_msgcontact() == ['test@example.com']
    assert scheduler.get_msgcontact(step="syn", index=1) == ['foo@bar.com']
    scheduler.add_msgcontact('another@email.com', step="syn", index=1)
    assert scheduler.get_msgcontact(step="syn", index=1) == ['foo@bar.com', 'another@email.com']
    scheduler.add_msgcontact(['new@email.com'], step="syn", index=1, clobber=True)
    assert scheduler.get_msgcontact(step="syn", index=1) == ['new@email.com']


def test_maxnodes():
    scheduler = OptionSchema().scheduler
    scheduler.set_maxnodes(4)
    assert scheduler.get_maxnodes() == 4


def test_maxthreads():
    scheduler = OptionSchema().scheduler
    scheduler.set_maxthreads(8)
    assert scheduler.get_maxthreads() == 8
