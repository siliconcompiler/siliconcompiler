import pytest


from siliconcompiler import Flowgraph, Project
from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def gcd_nop_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    return project


@pytest.fixture
def gcd_remote_test(gcd_nop_project, scserver, scserver_credential):
    def setup(use_slurm=False):
        # Start running an sc-server instance.
        cluster = "local"
        if use_slurm:
            cluster = "slurm"
        port = scserver(cluster=cluster)

        # Create the temporary credentials file, and set the project to use it.
        gcd_nop_project.set('option', 'credentials', scserver_credential(port))
        gcd_nop_project.set('option', 'remote', True)

        gcd_nop_project.set('option', 'nodisplay', True)

        return gcd_nop_project

    return setup


class InlinePool:
    '''Stands in for the client's download pool, running the work here.

    The real pool's workers are separate processes: nothing they run is visible
    to coverage, a failure inside one surfaces only through the error callback,
    and a test cannot assert on either. Running the same calls inline keeps the
    download path observable. It does skip the pickling of the Client that a
    real worker forces, so the tests that fetch results through the actual pool
    are the ones that keep that path honest.
    '''

    def __init__(self, *args, **kwargs):
        self.calls = []

    def apply_async(self, func, args=(), kwds=None, callback=None, error_callback=None):
        self.calls.append(args)
        try:
            result = func(*args, **(kwds or {}))
        except Exception as e:  # noqa: BLE001
            if error_callback:
                error_callback(e)
            return None
        if callback:
            callback(result)
        return None

    def close(self):
        pass

    def join(self):
        pass


@pytest.fixture
def inline_download_pool(monkeypatch):
    '''Make the client fetch results in this process instead of forking.'''
    pools = []

    def make_pool(*args, **kwargs):
        pool = InlinePool()
        pools.append(pool)
        return pool

    monkeypatch.setattr('siliconcompiler.remote.client.multiprocessing.Pool', make_pool)
    return pools
