import os
import pytest
import json
import multiprocessing
import platform
import shutil
import socket
import subprocess
import sys
import time

import os.path

import siliconcompiler

from pathlib import Path
from pyvirtualdisplay import Display
from unittest.mock import patch

from siliconcompiler import utils, ASICProject, Design
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import TaskScheduler
from siliconcompiler.utils.multiprocessing import _ManagerSingleton, MPManager
from siliconcompiler.apps import sc_server


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

    old_init = siliconcompiler.Project._init_run

    def mock_init(self):
        self.set('option', 'cachedir', cachedir)

        return old_init(self)

    monkeypatch.setattr(siliconcompiler.Project, '_init_run', mock_init)


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


@pytest.fixture(autouse=True)
def skip_eda(request):
    '''
    Limit CPU core count for eda tests
    '''
    if 'ready' in request.keywords:
        return
    if 'eda' in request.keywords:
        pytest.skip("EDA not ready")
    if 'docker' in request.keywords:
        pytest.skip("docker not ready")


@pytest.fixture(autouse=True)
def isolate_statics_in_testing(monkeypatch):
    '''
    Isolate static instances for testing
    '''

    monkeypatch.setattr(MPManager, "_MPManager__ENABLE_LOGGER", False)
    monkeypatch.setattr(MPManager, "_MPManager__address", None)

    with patch.dict(TaskScheduler._TaskScheduler__callbacks), \
            patch.dict(_ManagerSingleton._instances, clear=True):
        yield

        # Cleanup afterwards
        MPManager.stop()


@pytest.fixture(autouse=True)
def disable_or_images(monkeypatch, request):
    '''
    Disable OpenROAD image generation since this adds to the runtime
    '''
    if 'eda' not in request.keywords:
        return
    old_init = siliconcompiler.Project._init_run

    def mock_init(self: siliconcompiler.Project):
        tasks = self.get_task(filter=APRTask)
        if not isinstance(tasks, set):
            tasks = [tasks]
        for task in tasks:
            task.set('var', 'ord_enable_images', False, clobber=False)

        return old_init(self)

    monkeypatch.setattr(siliconcompiler.Project, '_init_run', mock_init)


@pytest.fixture(scope='session')
def test_dir(tmp_path_factory):
    yield tmp_path_factory.getbasetemp().parent


@pytest.fixture(autouse=True)
def mock_home(monkeypatch, test_dir):
    def _mock_home():
        return test_dir

    monkeypatch.setattr(Path, 'home', _mock_home)
    monkeypatch.setenv("HOME", str(test_dir))


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
    '''Returns a fully configured chip object that will compile the GCD example
    design using freepdk45 and the asicflow.'''

    project = ASICProject(heartbeat_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    project.set_flow(ASICFlow())

    project.load_target(freepdk45_demo.setup)

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
    '''Returns a fully configured chip object that will compile the GCD example
    design using freepdk45 and the asicflow.'''

    project = ASICProject(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    project.set_flow(ASICFlow())

    project.load_target(freepdk45_demo.setup)

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


@pytest.fixture
def scserver(scserver_nfs_path, unused_tcp_port, request, wait_for_port, monkeypatch):
    srv_proc = None

    def start_server(cluster='local', auth=False):
        nonlocal srv_proc

        args = [
            '-nfsmount', scserver_nfs_path,
            '-cluster', cluster,
            '-port', str(unused_tcp_port),
            '-checkinterval', '1'
        ]
        if auth:
            args.append('-auth')

        monkeypatch.setattr(sys, "argv", ["sc-server", *args])

        srv_proc = multiprocessing.Process(target=sc_server.main)
        srv_proc.start()

        # Wait for server to become available
        wait_for_port(unused_tcp_port)

        return unused_tcp_port

    def stop_server():
        if srv_proc:
            srv_proc.kill()

    request.addfinalizer(stop_server)

    return start_server


@pytest.fixture
def wait_for_port():
    def is_open(port, timeout=1):
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)

        try:
            test_socket.connect(('localhost', port))
            test_socket.shutdown(socket.SHUT_RDWR)
            return True
        except:  # noqa: E722
            return False
        finally:
            test_socket.close()

    def wait(port, timeout=20):
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

    def write(port, username=None, password=None, chip=None):
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

        if chip:
            chip.set('option', 'remote', True)
            chip.set('option', 'credentials', cred_file)

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
