import logging
import os
import pytest
import glob
import json
import re
import platform
import psutil
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time

import os.path

from contextlib import contextmanager
from uuid import uuid4
from pathlib import Path
from pyvirtualdisplay import Display
from unittest.mock import patch

from typing import Optional, Tuple

from siliconcompiler import utils, ASIC, Design, Project, OpenTask
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.utils.multiprocessing import _ManagerSingleton, MPManager, \
    get_process_context, forking
from siliconcompiler.apps import sc_server
from siliconcompiler.schema import BaseSchema


def pytest_addoption(parser):
    helpstr = ("Run all tests in current working directory. Default is to run "
               "each test in an isolated per-test temporary directory.")

    parser.addoption(
        "--cwd", action="store_true", help=helpstr
    )

    helpstr = ("Remove test after run.")

    parser.addoption(
        "--clean", action="store_true", help=helpstr
    )


@pytest.fixture(autouse=True)
def test_wrapper(tmp_path, request, monkeypatch):
    '''Fixture that automatically runs each test in a test-specific temporary
    directory to avoid clutter. To override this functionality, pass in the
    --cwd flag when you invoke pytest.'''
    if not request.config.getoption("--cwd"):
        monkeypatch.chdir(tmp_path)

        # Run the test.
        yield

        if request.config.getoption("--clean"):
            monkeypatch.undo()
            shutil.rmtree(tmp_path)
    else:
        yield


@pytest.fixture(autouse=True)
def use_cache(monkeypatch, request):
    '''Set [option, cachedir]
    '''
    if 'nocache' in request.keywords:
        return

    cachedir = os.getenv("SCTESTCACHE", None)
    if not cachedir:
        return

    old_init = Project._init_run

    def mock_init(self):
        self.set('option', 'cachedir', cachedir)

        return old_init(self)

    monkeypatch.setattr(Project, '_init_run', mock_init)


@pytest.fixture(autouse=True)
def limit_cpus(monkeypatch, request):
    '''
    Limit CPU core count for eda tests
    '''
    if 'eda' not in request.keywords:
        return
    if 'nocpulimit' in request.keywords:
        return

    org_cpus = utils.get_cores()

    def limit_cpu(*args, **kwargs):
        if org_cpus > 1:
            return 2
        return 1

    monkeypatch.setattr(utils, 'get_cores', limit_cpu)


class _SharedManagerServer:
    '''
    The session-wide manager server, see shared_manager_server().
    '''

    def __init__(self):
        self.__start()

    def __start(self) -> None:
        # Collecting some test modules builds a Project, which leaves an
        # MPManager behind. Drop it, or MPManager() below would hand that one
        # back without running _init_singleton() and there would be no address
        # to share.
        MPManager.stop()

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", False)
            monkeypatch.setattr(MPManager, "_MPManager__address", None)
            MPManager()

        self.__manager = MPManager.get_manager()
        self.address = self.__manager.address
        assert self.address is not None, "manager server did not report an address"
        self.__baseline = self.__manager._number_of_objects()

    def __is_pristine(self) -> bool:
        '''Is the server up and holding nothing a test put there?'''
        process = getattr(self.__manager, "_process", None)
        if process is None or not process.is_alive():
            return False
        try:
            return self.__manager._number_of_objects() == self.__baseline
        except OSError:
            # Socket gone: a hard-killed server whose address still resolves.
            return False

    def reset(self) -> None:
        '''Hand the next test a server as clean as a freshly started one.

        Normally there is nothing to do -- a test's proxies are released when
        its MPManager singleton is dropped. What survives is the occasional
        stranded server-side refcount, from a node worker killed before it
        could decref, plus a proxy here and there whose release has not been
        collected yet. Rather than unpicking the server's object table by hand,
        throw the server away and start another: measured at ~20 restarts
        across a full run, against the ~2000 this fixture exists to avoid.

        Also covers a test that shut the server down outright, which is why
        no test needs to declare that it might.
        '''
        if self.__is_pristine():
            return
        self.stop()
        self.__start()

    def stop(self) -> None:
        MPManager.stop()


@pytest.fixture(autouse=True, scope="session")
def shared_manager_server():
    '''
    Run one manager server process for the whole session.

    isolate_statics_in_testing() drops the MPManager singleton after every
    test, so without a pre-existing server every test that builds a Project
    would start one of its own: ~2000 manager processes over a full run. On
    Linux that is a fork and costs ~10ms, but macOS and Windows use spawn (see
    get_process_context()), which boots a fresh interpreter every time. That is
    slow on average and has a very long tail on a saturated CI runner -- long
    enough that SyncManager.start() alone has blown the pytest timeout while
    waiting on the new process to report its address.

    Handing the tests an address up front sends them down _init_singleton()'s
    connect() branch instead, which is a socket handshake against this one
    server, and reset() keeps that server as clean between tests as a fresh one
    would be. Everything else a test might dirty -- settings, the path cache,
    the board, the logger -- is in-process state that the singleton teardown
    already rebuilds from scratch.

    A test that needs to own its manager rather than connect to this one -- one
    asserting on the manager's own lifecycle -- opts out with
    @pytest.mark.isolated_manager.
    '''
    server = _SharedManagerServer()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(autouse=True)
def isolate_statics_in_testing(monkeypatch, request, shared_manager_server):
    '''
    Isolate static instances for testing
    '''

    isolated = 'isolated_manager' in request.keywords

    if not isolated:
        # Clean up after the previous test here rather than in this fixture's
        # own teardown. Teardown runs while the finishing test's monkeypatches
        # are still in place -- monkeypatch is a dependency, so it is undone
        # only once this fixture has finalized -- and talking to the manager
        # under them is not safe: a test that fakes sys.platform makes
        # multiprocessing reject the real address family ("Family AF_PIPE is
        # not recognized" on Windows). By setup time every such patch is gone.
        shared_manager_server.reset()

    monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", False)
    monkeypatch.setattr(MPManager, "_MPManager__address",
                        None if isolated else shared_manager_server.address)

    BaseSchema._BaseSchema__get_child_classes.cache_clear()
    BaseSchema._BaseSchema__load_schema_class.cache_clear()

    with patch.dict(_ManagerSingleton._instances, clear=True):
        yield

        # Cleanup afterwards
        MPManager.stop()


@pytest.fixture
def isolated_tasks(monkeypatch):
    """
    An OpenTask/ShowTask/ScreenshotTask registry holding only what the test puts in it.

    ``get_task()`` populates the registry by recursing every live ``OpenTask``
    subclass in the process and then loading the built-in viewers, so a test
    that registers doubles resolves against those as well -- including doubles
    left behind by other tests in the same module. Skip the discovery step;
    ``register_task()`` and ``get_task()`` are otherwise untouched.
    """
    monkeypatch.setattr(OpenTask, "_OpenTask__populate_tasks",
                        classmethod(lambda cls: None))


@pytest.fixture(autouse=True)
def disable_or_images(monkeypatch, request):
    '''
    Disable OpenROAD image generation since this adds to the runtime
    '''
    if 'eda' not in request.keywords:
        return

    old_init = Project._init_run

    def mock_init(self: Project):
        try:
            tasks = APRTask.find_task(self)
            if not isinstance(tasks, set):
                tasks = [tasks]
            for task in tasks:
                task.set('var', 'ord_enable_images', False, clobber=False)
        except ValueError:
            pass

        return old_init(self)

    monkeypatch.setattr(Project, '_init_run', mock_init)


class _FakeEntryPoint:
    '''
    Stand-in for importlib.metadata.EntryPoint that hands back an already-loaded object.
    '''

    def __init__(self, name, obj):
        self.name = name
        self.__obj = obj

    def load(self):
        return self.__obj


@pytest.fixture
def fake_plugins(monkeypatch):
    '''
    Register fake siliconcompiler entry points.

    SiliconCompiler registers no entry points of its own, so discovery is empty unless a
    test opts in. The returned callable takes the plugin group suffix (for example
    "showtask"), the entry point name, and the object the entry point should load to.
    '''

    registry = {}

    def register(system, name, obj):
        registry.setdefault(system, []).append(_FakeEntryPoint(name, obj))

    def fake_entry_points(group):
        prefix = "siliconcompiler."
        if not group.startswith(prefix):
            return []
        return list(registry.get(group[len(prefix):], []))

    monkeypatch.setattr(utils, "entry_points", fake_entry_points)

    return register


@pytest.fixture
def wait_for_child():
    '''
    Wait on a forked child, as ``(exited, exited_cleanly)``.

    Any child still running at the deadline is killed and reaped in teardown, so
    a test whose child deadlocks fails on its own assertions instead of wedging
    the run: a forked child holds the session's file descriptors open, and
    pytest will not finish while one of them is stuck.

    Returns a callable taking the pid and an optional timeout in seconds.
    '''
    running = []

    def wait(pid: int, timeout: float = 10) -> Tuple[bool, bool]:
        running.append(pid)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited:
                running.remove(pid)
                return True, os.waitstatus_to_exitcode(status) == 0
            time.sleep(0.05)
        return False, False

    yield wait

    for pid in running:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)


@pytest.fixture
def project_logger(monkeypatch):
    def setup(proj):
        test_logger = logging.getLogger("sc_test_" + str(uuid4()))
        test_logger.propagate = True
        test_logger.setLevel(logging.INFO)
        monkeypatch.setattr(proj, "_Project__logger", test_logger)

    return setup


@pytest.fixture(scope='session')
def test_dir(tmp_path_factory):
    yield tmp_path_factory.getbasetemp().parent


@pytest.fixture(autouse=True)
def mock_home(monkeypatch, test_dir):
    def _mock_home():
        return test_dir

    monkeypatch.setattr(Path, 'home', _mock_home)
    monkeypatch.setenv("HOME", str(test_dir))

    # Ensure a developer's ambient system settings file is never picked up
    # during tests; individual tests can opt back in with monkeypatch.setenv.
    monkeypatch.delenv("SC_SYSTEM_SETTINGS", raising=False)


@pytest.fixture(scope='session')
def scroot():
    '''Returns an absolute path to the SC root directory.'''
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def datadir(request):
    '''Returns an absolute path to the current test directory's local data
    directory.'''
    return os.path.abspath(os.path.join(os.path.dirname(request.fspath), 'data'))


@pytest.fixture
def heartbeat_design(examples_root):
    design = Design("heartbeat")
    design.set_dataroot("heartbeat-pytest-example", os.path.join(examples_root, 'heartbeat'))
    with design.active_fileset("rtl"), design.active_dataroot("heartbeat-pytest-example"):
        design.set_topmodule("heartbeat")
        design.add_file("heartbeat.v")
    with design.active_fileset("sdc"), design.active_dataroot("heartbeat-pytest-example"):
        design.add_file("heartbeat.sdc")
    return design


@pytest.fixture
def asic_heartbeat(heartbeat_design):
    '''Returns a fully configured project object that will compile the heartbeat example
    design using freepdk45 and the asicflow.'''

    project = ASIC(heartbeat_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    project.set_flow(ASICFlow())

    freepdk45_demo(project)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    return project


@pytest.fixture
def gcd_design(examples_root):
    design = Design("gcd")
    design.set_dataroot("gcd-pytest-example", os.path.join(examples_root, 'gcd'))
    with design.active_fileset("rtl"), design.active_dataroot("gcd-pytest-example"):
        design.set_topmodule("gcd")
        design.add_file("gcd.v")
    with design.active_fileset("sdc"), design.active_dataroot("gcd-pytest-example"):
        design.add_file("gcd.sdc")
    return design


@pytest.fixture
def asic_gcd(gcd_design):
    '''Returns a fully configured project object that will compile the GCD example
    design using freepdk45 and the asicflow.'''

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    project.set_flow(ASICFlow())

    freepdk45_demo(project)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    return project


@pytest.fixture(scope='session')
def examples_root(scroot):
    return os.path.join(scroot, 'examples')


@pytest.fixture
def scserver_nfs_path():
    work_dir = os.path.abspath('local_server_work')
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


@pytest.fixture
def scserver_users(scserver_nfs_path):
    def add_user(username, password):
        with open(os.path.join(scserver_nfs_path, 'users.json'), 'w') as f:
            f.write(json.dumps({'users': [{
                'username': username,
                'password': password,
            }]}))
    return add_user


def _shutdown_server(proc, timeout=10):
    '''
    Stop an sc-server process and everything it started.

    SIGTERM rather than SIGKILL: aiohttp installs a SIGTERM handler that turns it
    into a graceful exit of web.run_app(), so sc_server.main() returns and the
    server process runs its own teardown -- releasing its handles on the session
    manager and joining the node workers it forked. Under SIGKILL none of that
    happens, and whatever the server started is orphaned rather than collected.

    The recursive sweep afterwards is the backstop for a server that had to be
    killed after all: read the tree before signalling the parent, because once it
    is gone its children are reparented and no longer findable from here.
    '''
    if proc.pid is None:
        return

    try:
        descendants = psutil.Process(proc.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []

    proc.terminate()
    proc.join(timeout)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout)

    alive = [child for child in descendants if child.is_running()]
    for child in alive:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=timeout)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(alive, timeout=timeout)


@pytest.fixture
def scserver(scserver_nfs_path, unused_tcp_port, request, wait_for_port, monkeypatch):
    srv_procs = []

    def start_server(cluster='local', auth=False, extra_args=None):
        args = [
            '-nfsmount', scserver_nfs_path,
            '-cluster', cluster,
            '-port', str(unused_tcp_port),
            '-checkinterval', '1'
        ]
        if auth:
            args.append('-auth')
        if extra_args:
            args.extend(extra_args)

        monkeypatch.setattr(sys, "argv", ["sc-server", *args])

        # Launch with the start method the scheduler pins (fork on Linux), not
        # the interpreter default. Under the 3.14 default, forkserver, the server
        # comes up in a freshly exec'd interpreter that has none of this
        # session's state -- in particular no shared_manager_server address, so
        # it starts an MPManager server process of its own, which then has to be
        # cleaned up along with it.
        srv_proc = get_process_context().Process(target=sc_server.main)
        with forking():
            srv_proc.start()
        srv_procs.append(srv_proc)

        # Wait for server to become available
        wait_for_port(unused_tcp_port)

        return unused_tcp_port

    def stop_server():
        for srv_proc in srv_procs:
            _shutdown_server(srv_proc)

    request.addfinalizer(stop_server)

    return start_server


@pytest.fixture
def wait_for_port():
    def is_open(port: int, timeout: int = 1):
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(timeout)

        try:
            test_socket.connect(('localhost', port))
            test_socket.shutdown(socket.SHUT_RDWR)
            return True
        except:  # noqa: E722
            return False
        finally:
            test_socket.close()

    def wait(port: int, timeout: int = 20):
        for _ in range(timeout):
            if is_open(port):
                return
            else:
                time.sleep(1)
        pytest.skip(f"{port} failed to become available")

    return wait


@pytest.fixture
def scserver_credential():
    cred_file = "scserver_test_credentials.json"

    def write(port: int,
              username: Optional[str] = None,
              password: Optional[str] = None,
              project: Optional[Project] = None):
        creds = {
            'address': 'localhost',
            'port': port
        }
        if username:
            creds['username'] = username
        if password:
            creds['password'] = password

        with open(cred_file, 'w') as f:
            f.write(json.dumps(creds))

        if project:
            project.set('option', 'remote', True)
            project.set('option', 'credentials', cred_file)

        return cred_file

    return write


@pytest.fixture
def run_cli():
    def run(cmd, expect_file=None, stdout_to_pipe=False, retcode=0):
        if isinstance(cmd, str):
            cmd = [cmd]

        stdout = None
        capture_stdout = True
        if stdout_to_pipe:
            stdout = subprocess.PIPE
            capture_stdout = False

        proc = subprocess.run(cmd,
                              stdout=stdout,
                              capture_output=capture_stdout,
                              universal_newlines=True)

        assert proc.returncode == retcode, \
            f"\"{' '.join(cmd)}\" failed with exit code {proc.returncode} != {retcode}"

        if expect_file:
            assert os.path.exists(expect_file), \
                f"\"{' '.join(cmd)}\" failed to generate: {expect_file}"

        return proc

    return run


@pytest.fixture
def sbt_download_guard(request):
    '''Returns a context manager that converts an sbt dependency download
    failure into a skip.

    Wrap the run of any Chisel-based flow in it. If the run fails and the log of
    a node that failed shows sbt failing to fetch its dependencies, the test is
    skipped; every other failure propagates unchanged.'''

    # sbt resolves its own launcher and the Chisel jars from Maven Central (and
    # friends) on every run, so a rate limit (HTTP 429) or a network hiccup
    # fails the convert node for reasons unrelated to SiliconCompiler.
    errors = (
        "download error: Caught java.io.IOException",
        "could not retrieve sbt",
    )

    @contextmanager
    def guard():
        try:
            yield
        except Exception as e:
            # Only the logs of the nodes that actually failed count: coursier
            # reports the same download errors for mirrors it then successfully
            # falls back from, so those messages also sit in the logs of nodes
            # that ran fine and must not mask an unrelated failure.
            failed = re.search(r"due to errors in: (.*)", str(e))
            for node in failed.group(1).split(",") if failed else []:
                step, _, index = node.strip().partition("/")
                for log in glob.glob(os.path.join("**", step, index, "*.log"), recursive=True):
                    try:
                        with open(log, errors="ignore") as f:
                            text = f.read()
                    except OSError:
                        continue
                    for error in errors:
                        if error in text:
                            pytest.skip(f"{request.node.nodeid}: sbt failed to download its "
                                        f"dependencies ({error}) in {log}")
            raise

    return guard


@pytest.fixture
def has_graphviz():
    import graphviz
    try:
        graphviz.version()
    except graphviz.ExecutableNotFound:
        pytest.skip("graphviz not available")


@pytest.fixture
def display():
    if "WSL2" in platform.platform():
        os.environ["PYVIRTUALDISPLAY_DISPLAYFD"] = "0"

    if sys.platform != 'win32':
        display = Display(visible=False)
        display.start()
        yield display
        display.stop()
    else:
        yield False


@pytest.fixture
def disable_mp_process():
    class FakeProc:
        def __init__(self, target, args=()):
            self.target = target
            self.args = args
            self.exitcode = None

        def start(self):
            try:
                self.target(*self.args)
                self.exitcode = 0
            except SystemExit as e:
                self.exitcode = e.code

        def join(self):
            return

        def is_alive(self):
            return False

    # The scheduler launches node workers via get_process_context().Process
    # (a context-specific Process class), not the module-level
    # multiprocessing.Process, so we fake the context: Process runs the target
    # inline while get_start_method/Queue/Pipe/Pool delegate to the real
    # context. Delegate to siliconcompiler's get_process_context() (not the
    # interpreter default) so the faked start method matches what the scheduler
    # actually uses -- e.g. "fork" on Linux, not the 3.14 "forkserver" default.
    real_ctx = get_process_context()

    class FakeContext:
        Process = FakeProc

        def get_start_method(self, *args, **kwargs):
            return real_ctx.get_start_method(*args, **kwargs)

        def Queue(self, *args, **kwargs):
            return real_ctx.Queue(*args, **kwargs)

        def Pipe(self, *args, **kwargs):
            return real_ctx.Pipe(*args, **kwargs)

        def Pool(self, *args, **kwargs):
            return real_ctx.Pool(*args, **kwargs)

    fake_ctx = FakeContext()
    with patch("siliconcompiler.scheduler.taskscheduler.get_process_context",
               return_value=fake_ctx), \
         patch("siliconcompiler.scheduler.scheduler.get_process_context",
               return_value=fake_ctx):
        yield


@pytest.fixture
def broken_tarfile_data_filter(monkeypatch):
    """
    Makes this interpreter look like one that misreads relative symlinks.

    Python 3.8.17, 3.9.17, 3.10.12 and 3.11.4 shipped the first PEP 706 backport,
    which resolved a symlink's target from the extraction root instead of from the
    directory holding the link (fixed by CPython gh-107845). A relative symlink
    into a sibling directory -- as the IHP130 PDK ships -- looked to them like an
    escape from the destination. ``requires-python`` admits those releases, so the
    workaround in :func:`siliconcompiler.utils.tar_extract_kwargs` has to be
    exercised somewhere other than on them.

    A release older still -- anything before the backport -- has no extraction
    filter to stand in for, and extracts the link without complaint, so there is
    nothing for these tests to exercise there.

    Yields:
        The stand-in filter, for a test that wants to pass it to ``extractall``
        directly rather than through ``tar_extract_kwargs``.
    """
    if not hasattr(tarfile, "data_filter"):
        pytest.skip("release predates the PEP 706 extraction filters")

    real = tarfile.data_filter

    def broken(member, dest_path):
        # Only the containment checks are reproduced, in the order the old filter
        # ran them -- a member's own name before its link target. Everything else
        # is left to the real filter.
        dest = os.path.realpath(dest_path)

        name = member.name.lstrip("/" + os.sep)
        target = os.path.realpath(os.path.join(dest, name))
        if os.path.commonpath([target, dest]) != dest:
            raise tarfile.OutsideDestinationError(member, target)

        if (member.issym() or member.islnk()) and not os.path.isabs(member.linkname):
            target = os.path.realpath(os.path.join(dest, member.linkname))
            if os.path.commonpath([target, dest]) != dest:
                raise tarfile.LinkOutsideDestinationError(member, target)

        return real(member, dest_path)

    monkeypatch.setattr(tarfile, "data_filter", broken)
    utils._data_filter_mishandles_symlinks.cache_clear()
    yield broken
    utils._data_filter_mishandles_symlinks.cache_clear()
