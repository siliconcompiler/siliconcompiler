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
