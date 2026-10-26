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
        "scope": ("jobs:read jobs:write jobs:delete artifacts:read devices:read "
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
    # Login read `GET /v1`; a test that serves another one expects to see it.
    client.transport.forget_published()
    return client


@pytest.fixture
def tmp_credentials():
    '''Credentials in the test's own directory, never the real ~/.sc.'''
    from pathlib import Path

    from siliconcompiler.remote import Credentials

    creds = Credentials(Path("sc-home/auth/remote.json"))
    creds.set_server(V1_URL.rsplit("/v1", 1)[0])
    return creds


@pytest.fixture
def key():
    from siliconcompiler.remote import dpop

    return dpop.generate_key()


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

            chosen = owners.collection(owners.walk(project), lambda one: one.upload)
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


#
# The real server, from `create_app`, in the test's own directory.

BASE = "http://localhost"


@pytest.fixture
def server():
    pytest.importorskip("flask", reason="the server extra is not installed")

    from siliconcompiler.remote.server.app import create_app

    return create_app("sc-server", cluster="local")


@pytest.fixture
def server_client(server):
    return server.test_client()


@pytest.fixture
def live_server(server):
    '''The server on a real socket and thread, for the real client.'''
    import threading

    from werkzeug.serving import make_server

    httpd = make_server("127.0.0.1", 0, server, threaded=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=10)


def slug(response):
    '''The condition a refusal named, which is what a client branches on.'''
    return ((response.get_json() or {}).get("type") or "").rsplit("/", 1)[-1]


def proof(key, method, path, token=None):
    from siliconcompiler.remote import dpop

    return dpop.sign_proof(key, method, BASE + path, access_token=token)


def login(client, key, subject="machine:1000", **extra):
    form = {"grant_type": "client_credentials", "client_id": f"local:{subject}", **extra}
    return client.post("/v1/auth/token", data=form,
                       headers={"DPoP": proof(key, "POST", "/v1/auth/token")})


def call(client, key, method, path, token, headers=None, **kwargs):
    '''One authenticated request, proof and all.'''
    return client.open(path, method=method, headers={
        "Authorization": f"DPoP {token}",
        "DPoP": proof(key, method, path.split("?")[0], token), **(headers or {})}, **kwargs)


@pytest.fixture
def token(server_client, key):
    return login(server_client, key).get_json()["access_token"]


#
# The job path: a caller, a dispatcher that starts nothing, and a submitted job.

class FakeDispatcher:
    '''Starts nothing: a test writes the run's progress itself. `gate`, set,
    holds `submit` until released, so staging can be caught half-way.'''

    def __init__(self):
        import threading

        self.submitted, self.cancelled = [], []
        self.alive = True
        self.entered, self.gate = threading.Event(), threading.Event()
        self.gate.set()

    def submit(self, job_id, jobroot, manifest):
        self.entered.set()
        assert self.gate.wait(10)
        self.submitted.append(job_id)
        return f"fake:{job_id}"

    def is_alive(self, scheduler_job_id):
        return self.alive

    def cancel(self, scheduler_job_id, node_names=()):
        self.cancelled.append(scheduler_job_id)
        self.alive = False


@pytest.fixture
def dispatcher(server):
    server.config["SC_JOBS"].dispatcher = FakeDispatcher()
    return server.config["SC_JOBS"].dispatcher


def _caller(client, key, subject):
    token = login(client, key, subject=subject).get_json()["access_token"]

    def send(method, path, **kwargs):
        return call(client, key, method, path, token, **kwargs)
    return send


@pytest.fixture
def api(server_client, key):
    return _caller(server_client, key, "machine:1000")


@pytest.fixture
def stranger(server_client):
    from siliconcompiler.remote import dpop

    return _caller(server_client, dpop.generate_key(), "machine:2000")


def raw_archive(members):
    '''An archive of ``{name: bytes}``, as ``(path, digest, size)``.'''
    import hashlib
    import io
    import tarfile

    with tarfile.open("raw.tar.gz", "w:gz") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))

    with open("raw.tar.gz", "rb") as f:
        body = f.read()
    return os.path.abspath("raw.tar.gz"), f"sha256:{hashlib.sha256(body).hexdigest()}", len(body)


def upload(server_client, api, job_id, archive, sent=None):
    '''Grant and PUT an archive; ``sent`` are the bytes to PUT where they differ.'''
    from urllib.parse import urlsplit

    path, digest, size = archive
    grant = api("POST", f"/v1/jobs/{job_id}/upload-grant",
                json={"size_bytes": size, "digest": digest}).get_json()
    target = urlsplit(grant["url"])
    with open(path, "rb") as f:
        body = f.read() if sent is None else sent
    return server_client.put(f"{target.path}?{target.query}", data=body)


def settle(api, job_id, states=("staging",)):
    '''The job, once it has left ``states``: staging runs on a thread.'''
    import time

    end = time.time() + 10
    while True:
        job = api("GET", f"/v1/jobs/{job_id}").get_json()
        if job["state"] not in states or time.time() > end:
            return job
        time.sleep(0.05)


@pytest.fixture
def submit(server_client, api, job_archive):
    '''Create, upload and submit a job; returns the job as submit answered.'''
    def go(archive=None, jobname="job0", settled=True):
        job = api("POST", "/v1/jobs", json={"design": "gcd", "jobname": jobname}).get_json()
        assert upload(server_client, api, job["id"], archive or job_archive()).status_code == 204
        response = api("POST", f"/v1/jobs/{job['id']}/submit", json={})
        assert response.status_code == 202
        return settle(api, job["id"]) if settled else response.get_json()
    return go


def write_progress(server, job, state, nodes=None, **extra):
    '''What the runner would have written for this job.'''
    from siliconcompiler.remote.server.running import runspec

    root = server.config["SC_JOBS"].root(job["owner"]["id"], job["id"])
    nodes = nodes or {"stepone/0": state, "steptwo/0": state}
    runspec.write_json(root / runspec.PROGRESS_FILENAME, {
        "state": state, "started_at": 1000.0, "finished_at": None, **extra,
        "nodes": {name: {"state": node, "started_at": 1000.0, "finished_at": None,
                         "exit_code": None} for name, node in nodes.items()}})


@pytest.fixture
def tree(server, submit):
    '''A submitted job and what its run leaves in the tree.'''
    job = submit()
    root = server.config["SC_JOBS"].root(job["owner"]["id"], job["id"]) / "gcd" / "job0"
    for step in ("stepone", "steptwo"):
        (root / step / "0" / "outputs").mkdir(parents=True)
        (root / step / "0" / f"sc_{step}_0.log").write_text(f"{step} ran\n")
        (root / step / "0" / "outputs" / "gcd.pkg.json").write_text("{}")
    (root / "job.log").write_text("the flow\n")
    return job, root


def finish(server, api, dispatcher, job):
    '''End the run, and read the job so the server notices.'''
    write_progress(server, job, "completed", finished_at=1010.0)
    dispatcher.alive = False
    api("GET", f"/v1/jobs/{job['id']}")
