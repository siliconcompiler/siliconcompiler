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


###########################
# The conformance rig
###########################
#
# Two rigs test the remote half and they do different jobs. The integration rig
# is the compose stack under setup/server/: a real store, a real scheduler and
# real bytes, proving that the two halves work together. This is the other one.
#
# It answers the client's requests with whatever a test needs to see, and it is
# the only place most of the contract can be reached from. A working server
# cannot be made to emit `use_dpop_nonce` on demand, or report the device limit
# as exceeded, or refuse `projects` as unsupported, or hand back the HTML 502 a
# proxy in front of it would -- and the client branches on every one of those.
# So client branch coverage here is a function of the contract's frozen
# registry rather than of what a real server happens to say.
#
# No store, no scheduler, no jobs, no bytes, no port. Routes are added by the
# phase that needs them.

V1_URL = "https://sc-server.test/v1"


class FakeV1:
    '''A v1 server that exists only as a set of canned answers.

    Held by the `fake_v1` fixture. Register a route with `route()`; the last
    registration for a method and path wins, so a test can override anything
    the fixture set up for it.
    '''

    def __init__(self, mock, base_url):
        self._mock = mock
        self.base_url = base_url

    def url(self, path=""):
        '''The absolute URL of a path under this server.

        Joined rather than urljoin()'d on purpose: urljoin drops the version
        prefix off a base like `https://host/v1`, which is the bug the client
        rewrite has to avoid on day one.
        '''
        if not path:
            return self.base_url
        return f"{self.base_url}/{path.lstrip('/')}"

    def route(self, method, path, body, status=200,
              content_type="application/json", headers=None):
        '''Answer one request.'''
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body)
        self._mock.add(method, self.url(path), body=body, status=status,
                       content_type=content_type, headers=headers)

    def replace(self, method, path, body, status=200,
                content_type="application/json", headers=None):
        '''Change an answer this fixture already set up.

        Registrations are consumed in order, so adding a second one for a path
        queues it behind the first rather than replacing it -- which is what a
        test wants for a sequence and never what it wants for a fixture's
        default.
        '''
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body)
        self._mock.replace(method, self.url(path), body=body, status=status,
                           content_type=content_type, headers=headers)

    def elsewhere(self, method, url, body="", status=200,
                  content_type="application/json", headers=None):
        '''Answer a request to somewhere that is not this server.

        Storage is the case this exists for: the upload goes to whatever the
        grant points at, which on another deployment is a bucket on a different
        origin -- so a test that registered it under this server's base would be
        testing a shape the contract does not promise.
        '''
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body)
        self._mock.add(method, url, body=body, status=status,
                       content_type=content_type, headers=headers)

    @property
    def calls(self):
        '''Every request made, in order.'''
        return self._mock.calls


@pytest.fixture
def capabilities(datadir):
    '''The GET /v1 body, as the sc-server profile publishes it.

    A file rather than a literal: it is the one block whose every member has to
    be real from day one, both halves of the client's `limits` combine read it,
    and a server test can assert against the same bytes the client is given.
    '''
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
    '''An RFC 9457 body, built the way a server would build it.

    Written here rather than imported from the server so that a client test
    does not pass merely because both halves share a bug. The URI is the
    contract's, which is what a client branches on.
    '''
    return {
        "type": f"https://siliconcompiler.com/server-errors/{slug}",
        "title": slug.replace("-", " ").capitalize(),
        "status": status,
        **members,
    }


@pytest.fixture
def fake_v1(capabilities):
    '''A v1 server answering in-process, with GET /v1 already registered.

    Discovery is the first call on every path and carries no credential, so it
    is set up here rather than in each test. assert_all_requests_are_fired is
    off because a test that never reaches discovery is testing something real.
    '''
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        server = FakeV1(mock, V1_URL)
        server.route(responses.GET, "", capabilities)
        yield server


@pytest.fixture
def logged_in(fake_v1, client_credentials, tmp_credentials):
    '''A client that has a session, for tests about what comes after one.'''
    from siliconcompiler.remote import Client

    fake_v1.route(responses.POST, "auth/token", client_credentials)

    client = Client(tmp_credentials)
    client.login()
    return client


@pytest.fixture
def tmp_credentials():
    '''Credentials in this test's own directory.

    Never the real ~/.sc: these tests generate a key and write tokens, and a
    suite that touched the developer's own credentials would be rewriting the
    machine's identity.
    '''
    from pathlib import Path

    from siliconcompiler.remote import Credentials

    creds = Credentials(Path("sc-home/credentials"))
    creds.update(address=V1_URL.rsplit("/v1", 1)[0])
    return creds


###########################
# The integration rig, in-process
###########################
#
# The other half: a real store, a real archive, a real dispatcher and a real
# run, against `app.test_client()`. No port and no event loop -- seventeen of
# this profile's eighteen endpoints are request-in, response-out, which is what
# Flask was chosen for.

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
def key():
    from siliconcompiler.remote import dpop

    return dpop.generate_key()


@pytest.fixture
def token(server_client, key):
    return login(server_client, key).get_json()["access_token"]


@pytest.fixture
def nop_project(gcd_nop_project):
    '''A two-node flow that needs no EDA tool, ready to be packed and sent.'''
    gcd_nop_project.option.set_nodashboard(True)
    gcd_nop_project.option.set_jobname("job0")
    gcd_nop_project.option.set_builddir(os.path.abspath("build"))
    return gcd_nop_project


@pytest.fixture
def job_archive(nop_project):
    '''Build the archive a client would PUT, and report it as storage would.

    Returns ``(path, digest, size)``. The manifest goes inside rather than
    beside: the server re-derives every advisory value from it, so it has to
    arrive with the bytes it describes.
    '''
    import hashlib
    import tarfile

    from siliconcompiler.utils.paths import jobdir

    def build(project=None, extra=None):
        project = project or nop_project

        root = jobdir(project)
        os.makedirs(root, exist_ok=True)
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
