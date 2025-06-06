import copy
import os
import pytest
import siliconcompiler
from siliconcompiler import utils
from siliconcompiler.tools import openroad
from siliconcompiler.tools._common import get_tool_tasks
from siliconcompiler.targets import freepdk45_demo
from pathlib import Path
import subprocess
import json
import shutil
import socket
import time
from siliconcompiler.scheduler import TaskScheduler
from unittest.mock import patch


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
def use_strict(monkeypatch, request):
    '''Set [option, strict] to True for all Chip objects created in test
    session.

    This helps catch bugs.
    '''
    if 'nostrict' in request.keywords:
        return

    old_init = siliconcompiler.Chip.__init__

    def mock_init(chip, design, **kwargs):
        old_init(chip, design, **kwargs)
        chip.set('option', 'strict', True)

    monkeypatch.setattr(siliconcompiler.Chip, '__init__', mock_init)


@pytest.fixture(autouse=True)
def limit_cpus(monkeypatch, request):
    '''
    Limit CPU core count for eda tests
    '''
    if 'eda' not in request.keywords:
        return
    if 'nocpulimit' in request.keywords:
        return

    org_cpus = utils.get_cores(siliconcompiler.Chip("dummy"))

    def limit_cpu(*args, **kwargs):
        if org_cpus > 1:
            return 2
        return 1

    monkeypatch.setattr(utils, 'get_cores', limit_cpu)


@pytest.fixture(autouse=True)
def isolate_callbacks():
    '''
    Isolate callbacks for testing
    '''

    callbacks = TaskScheduler._TaskScheduler__callbacks
    with patch.dict(callbacks):
        yield


@pytest.fixture(autouse=True)
def disable_or_images(monkeypatch, request):
    '''
    Disable OpenROAD image generation since this adds to the runtime
    '''
    if 'eda' not in request.keywords:
        return
    old_run = siliconcompiler.Chip.run

    def mock_run(chip, raise_exception=False):
        for task in get_tool_tasks(chip, openroad):
            chip.set('tool', 'openroad', 'task', task, 'var', 'ord_enable_images', 'false',
                     clobber=False)

        return old_run(chip, raise_exception=raise_exception)

    monkeypatch.setattr(siliconcompiler.Chip, 'run', mock_run)


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
def gcd_chip(examples_root):
    '''Returns a fully configured chip object that will compile the GCD example
    design using freepdk45 and the asicflow.'''

    chip = siliconcompiler.Chip('gcd')
    chip.register_source('gcd-pytest-example', os.path.join(examples_root, 'gcd'))
    chip.use(freepdk45_demo)
    chip.input('gcd.v', package='gcd-pytest-example')
    chip.input('gcd.sdc', package='gcd-pytest-example')
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])
    chip.set('option', 'nodisplay', True)
    chip.set('option', 'quiet', True)

    return chip


@pytest.fixture(scope='session')
def gcd_chip_dir(tmpdir_factory, examples_root):
    '''Returns a fully configured chip object that will compile the GCD example
    design using freepdk45 and the asicflow.'''

    cwd = os.getcwd()
    rundir = str(tmpdir_factory.mktemp("gcd"))
    os.chdir(rundir)

    chip = siliconcompiler.Chip('gcd')
    chip.register_source('gcd-pytest-example', os.path.join(examples_root, 'gcd'))
    chip.use(freepdk45_demo)
    chip.input('gcd.v', package='gcd-pytest-example')
    chip.input('gcd.sdc', package='gcd-pytest-example')
    chip.set('constraint', 'outline', [(0, 0), (100.13, 100.8)])
    chip.set('constraint', 'corearea', [(10.07, 11.2), (90.25, 91)])
    chip.set('option', 'nodisplay', True)
    chip.set('option', 'quiet', True)

    assert chip.run()

    os.chdir(cwd)

    return chip, rundir


@pytest.fixture(scope='session')
def heartbeat_chip_dir(tmpdir_factory, scroot):
    '''Fixture that creates a heartbeat build directory by running a build.
    '''

    cwd = os.getcwd()
    rundir = str(tmpdir_factory.mktemp("heartbeat"))
    os.chdir(rundir)

    chip = siliconcompiler.Chip('heartbeat')
    chip.register_source('heartbeat-pytest', os.path.join(scroot, 'tests', 'data'))
    chip.set('option', 'loglevel', 'error')
    chip.set('option', 'quiet', True)
    chip.input('heartbeat.v', package='heartbeat-pytest')
    chip.input('heartbeat.sdc', package='heartbeat-pytest')
    chip.use(freepdk45_demo)
    assert chip.run()

    os.chdir(cwd)

    return chip, rundir


@pytest.fixture
def copy_chip_dir():
    def gen_copy(chip_dir, output="./"):
        chip, rundir = chip_dir

        shutil.copytree(rundir, output, dirs_exist_ok=True)

        new_chip = copy.deepcopy(chip)
        new_chip.cwd = os.path.abspath(output)
        return new_chip

    return gen_copy


@pytest.fixture(scope='session')
def examples_root(scroot):
    return os.path.join(scroot, 'examples')


@pytest.fixture
def caplogger():
    log_handler = None
    file_content = None
    _chip = None

    def close():
        nonlocal log_handler
        nonlocal file_content

        if not log_handler:
            return file_content

        log_handler.flush()
        with open(log_handler.baseFilename) as f:
            file_content = f.read()

        _chip.logger.removeHandler(log_handler)
        log_handler = None

        return file_content

    def install(chip, path="pytest-testing.log"):
        nonlocal log_handler
        nonlocal _chip
        _chip = chip

        log_handler = _chip._add_file_logger(path)

        return close

    return install


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
def scserver(scserver_nfs_path, unused_tcp_port, request, wait_for_port):
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

        srv_proc = subprocess.Popen(['sc-server', *args])  # noqa: F841

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
