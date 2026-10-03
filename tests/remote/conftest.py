import json
import os

import pytest
import responses

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


@pytest.fixture(autouse=True)
def machine_fingerprint(monkeypatch):
    '''A machine id where the host has none (a container often lacks
    /etc/machine-id), since the client refuses to sign in without one.'''
    from siliconcompiler.remote.client import identity

    real = identity.machine_fingerprint
    if real()[1] == "none":
        monkeypatch.setattr(identity, "machine_fingerprint",
                            lambda: ("a-test-host", "linux_machine_id"))
    return real


###########################
# The conformance rig
###########################
#
# Canned answers, for what a working server cannot be made to say on demand
# (`use_dpop_nonce`, a device limit exceeded, a proxy's HTML 502) and the client
# branches on. The compose stack under setup/server/ is the integration rig.

V1_URL = "https://sc-server.test/v1"


def _encoded(body):
    return body if isinstance(body, (str, bytes)) else json.dumps(body)


class FakeV1:
    '''A v1 server that is only canned answers; the last `route()` for a
    method and path wins.'''

    def __init__(self, mock, base_url):
        self._mock = mock
        self.base_url = base_url

    def url(self, path=""):
        '''Joined, not urljoin()'d: urljoin drops the `/v1` prefix.'''
        if not path:
            return self.base_url
        return f"{self.base_url}/{path.lstrip('/')}"

    def route(self, method, path, body, status=200,
              content_type="application/json", headers=None):
        '''Answer one request.'''
        self._mock.add(method, self.url(path), body=_encoded(body), status=status,
                       content_type=content_type, headers=headers)

    def replace(self, method, path, body, status=200,
                content_type="application/json", headers=None):
        '''Change an answer already set up; a second `route()` would queue
        behind it instead.'''
        self._mock.replace(method, self.url(path), body=_encoded(body), status=status,
                           content_type=content_type, headers=headers)

    def elsewhere(self, method, url, body="", status=200,
                  content_type="application/json", headers=None):
        '''Answer a request to another origin, such as a storage grant's.'''
        self._mock.add(method, url, body=_encoded(body), status=status,
                       content_type=content_type, headers=headers)

    @property
    def calls(self):
        '''Every request made, in order.'''
        return self._mock.calls


@pytest.fixture
def capabilities(datadir):
    '''The GET /v1 body, as the sc-server profile publishes it.'''
    with open(os.path.join(datadir, "capabilities.json")) as f:
        return json.load(f)


@pytest.fixture
def client_credentials():
    '''A shape-correct token response, for tests that are not about login.'''
    return {
        "access_token": "access-token-one",
        "token_type": "DPoP",
        "expires_in": 900,
        "refresh_token": "refresh-token-one",
        "refresh_token_expires_in": 604800,
        "session_expires_in": 1036800,
        "scope": ("jobs:read jobs:write artifacts:read devices:read "
                  "devices:write profile:read"),
    }


def problem(slug, status, **members):
    '''An RFC 9457 body, written here rather than imported from the server so
    a client test cannot pass on a bug both halves share.'''
    return {
        "type": f"https://siliconcompiler.com/server-errors/{slug}",
        "title": slug.replace("-", " ").capitalize(),
        "status": status,
        **members,
    }


@pytest.fixture
def fake_v1(capabilities):
    '''A v1 server answering in-process, GET /v1 already registered.'''
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        server = FakeV1(mock, V1_URL)
        server.route(responses.GET, "", capabilities)
        yield server


@pytest.fixture
def logged_in(fake_v1, client_credentials, tmp_credentials):
    '''A client that has a session.'''
    from siliconcompiler.remote import Client

    fake_v1.route(responses.POST, "auth/token", client_credentials)

    client = Client(tmp_credentials)
    client.login()
    return client


@pytest.fixture
def tmp_credentials():
    '''Credentials in the test's own directory, never the real ~/.sc.'''
    from pathlib import Path

    from siliconcompiler.remote import Credentials

    creds = Credentials(Path("sc-home/auth/remote.json"))
    creds.set_server(V1_URL.rsplit("/v1", 1)[0])
    return creds


###########################
# The integration rig, in-process
###########################
#
# A real store, archive, dispatcher and run, against `app.test_client()`.

BASE = "http://localhost/v1"


def slug(response):
    '''The condition a refusal named, which is what a client branches on.'''
    body = response.get_json() or {}
    return (body.get("type") or "").rsplit("/", 1)[-1]


def login(client, key, subject="machine:1000", **extra):
    from siliconcompiler.remote import dpop

    form = {"grant_type": "client_credentials",
            "client_id": f"local:{subject}", **extra}
    return client.post(
        "/v1/auth/token", data=form,
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")


def call(client, key, method, path, token, **kwargs):
    '''One authenticated request, proof and all.'''
    from siliconcompiler.remote import dpop

    url = "http://localhost" + path
    return client.open(
        path, method=method,
        headers={"Authorization": f"DPoP {token}",
                 "DPoP": dpop.sign_proof(key, method, url, access_token=token),
                 **(kwargs.pop("headers", None) or {})},
        **kwargs)


def read(client, key, token, job_id):
    '''The job object, as GET /v1/jobs/{id} answers it.'''
    return call(client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()


def stranger(client, subject="machine:1001"):
    '''Another user on the same server: their key and token.'''
    from siliconcompiler.remote import dpop

    other = dpop.generate_key()
    return other, login(client, other, subject=subject).get_json()["access_token"]


@pytest.fixture(autouse=True)
def staging_inline(request, monkeypatch):
    '''Staging runs in the submitting request's thread, after the `202` body
    is computed, so one GET reads the outcome. `threaded_staging` opts out.'''
    if request.node.get_closest_marker("threaded_staging"):
        return
    try:
        from siliconcompiler.remote.server.jobs import JobService
    except ImportError:
        return

    def inline(self, job_id):
        with self._preparing_lock:
            if job_id in self._preparing:
                return
            self._preparing.add(job_id)
        self._prepare(job_id)

    monkeypatch.setattr(JobService, "_start_preparing", inline)


# The one SiliconCompiler version the tests' registries hold (profile §5).
TEST_SC_VERSION = "0.38.0"


@pytest.fixture
def runs_test_version(monkeypatch):
    '''The server under test runs `TEST_SC_VERSION`.'''
    try:
        from siliconcompiler.remote.server.software import images
    except ImportError:
        return
    monkeypatch.setattr(images, "own_version", lambda: TEST_SC_VERSION)


@pytest.fixture(autouse=True)
def manifest_read_inline(request, monkeypatch):
    '''The manifest is read in the test process, so a task class a test
    defines resolves. `real_read` keeps the contained subprocess.'''
    if request.node.get_closest_marker("real_read"):
        return
    try:
        from siliconcompiler.remote.server.staging import manifestread
        from siliconcompiler.remote.server.jobs import JobService
    except ImportError:
        return

    def inline(self, job, root, asked):
        summary = manifestread.read(json.loads(json.dumps(asked)))
        summary.update(contained={"network": False, "limits": False}, seconds=0)
        # Through JSON, as the subprocess's answer is.
        return json.loads(json.dumps(summary))

    monkeypatch.setattr(JobService, "_run_read", inline)


def run_manifest(manifest):
    '''The project a dispatched run executes: the manifest with the server's
    overrides applied, as the runner applies them.'''
    from siliconcompiler import Project
    from siliconcompiler.remote.server.running import runspec

    project = Project.from_manifest(filepath=str(manifest))
    run = runspec.read_run(runspec.state_dir(manifest) / runspec.RUN_FILENAME)
    if run is not None:
        runspec.apply_run(project, run)
    return project


def job_after(client, key, token, response):
    '''The job a `202` submit answered for, as it stands once staging ran.'''
    return read(client, key, token, response.get_json()['id'])


class _JobError:
    '''A job's `error`, read the way a refusal of the request is.'''

    def __init__(self, error):
        self._error = error
        self.status_code = error.get("status")

    def get_json(self):
        return self._error


def outcome(client, key, token, response):
    '''What a submit came to: the refusal as answered or, after a `202`, the
    error staging put on the job, where it has one.'''
    if response.status_code != 202:
        return response
    error = job_after(client, key, token, response).get("error")
    return _JobError(error) if error else response


class FakeDispatcher:
    '''Records what it was asked to run and never runs it: a refusal that
    reached it would be a bug. `cluster="local"` is the real run.'''

    name = "fake"

    def __init__(self):
        self.submitted = []
        self.cancelled = []
        self.cancelled_nodes = []
        self.still_running = set()
        self.handed = {}
        self.alive = True

    def submit(self, job_id, jobroot, manifest, image=None, queue=None):
        self.submitted.append((job_id, jobroot, manifest))
        self.handed = {"image": image, "queue": queue}
        return f"fake:{len(self.submitted)}"

    def is_alive(self, scheduler_job_id):
        return self.alive

    def cancel(self, scheduler_job_id, node_job_ids=()):
        # None is "only the orphans": the run is gone, and a real dispatcher
        # does not scancel a finished job.
        if scheduler_job_id:
            self.cancelled.append(scheduler_job_id)
        self.cancelled_nodes = list(node_job_ids)

    def node_jobs(self, job_id, nodes):
        # One scheduler id per node, by a name the server can derive.
        return {node: f"{job_id}_{node[0]}_{node[1]}" for node in nodes}

    def running_nodes(self, job_id, nodes):
        return [f"{job_id}_{step}_{index}" for step, index in nodes
                if (step, index) in self.still_running]

    def describe(self, scheduler_job_id):
        return f"the scheduler's record of {scheduler_job_id}"


@pytest.fixture
def server():
    '''A server on its own datadir, dispatching locally.'''
    pytest.importorskip("flask", reason="the server extra is not installed")

    from siliconcompiler.remote.server.app import create_app

    return create_app("datadir", cluster="local")


@pytest.fixture
def server_client(server):
    return server.test_client()


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def key():
    from siliconcompiler.remote import dpop

    return dpop.generate_key()


@pytest.fixture
def token(server_client, key):
    return login(server_client, key).get_json()["access_token"]


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


@pytest.fixture
def nop_project(gcd_nop_project):
    '''A two-node flow that needs no EDA tool, ready to be packed and sent.'''
    gcd_nop_project.option.set_nodashboard(True)
    gcd_nop_project.option.set_jobname("job0")
    gcd_nop_project.option.set_builddir(os.path.abspath("build"))
    return gcd_nop_project


@pytest.fixture
def python_project(nop_project):
    '''The two-node flow, its first node running the user's Python.'''
    from pytasks import RunsPython

    flow = Flowgraph("pyflow")
    flow.node("stepone", RunsPython())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    nop_project.set_flow(flow)
    return nop_project


@pytest.fixture
def job_archive(nop_project):
    '''Build the archive a client would PUT: ``(path, digest, size)``. The
    manifest goes inside, since the server re-derives everything from it.'''
    import hashlib
    import tarfile

    from siliconcompiler.utils.paths import jobdir

    def build(project=None, extra=None, collect_files=True):
        project = project or nop_project

        root = jobdir(project)
        os.makedirs(root, exist_ok=True)
        if collect_files:
            # What a real client sends: the files it uploads by owner, collected.
            from siliconcompiler.remote import owners
            from siliconcompiler.utils.curation import collect

            chosen = owners.collection(project, lambda one: owners.uploads(
                project, one.key, one.dataroot, one.resolvers))
            collect(project, verbose=False, keys=chosen.keys, select=chosen.select)
        project.write_manifest(os.path.join(root, f"{project.name}.pkg.json"))

        path = os.path.abspath(f"upload-{project.name}-{project.option.get_jobname()}.tar.gz")
        with tarfile.open(path, "w:gz") as tar:
            tar.add(root, arcname="")
            for name, body in (extra or {}).items():
                import io
                info = tarfile.TarInfo(name)
                info.size = len(body)
                tar.addfile(info, io.BytesIO(body))

        digest = hashlib.sha256()
        size = 0
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)

        return path, f"sha256:{digest.hexdigest()}", size

    return build
