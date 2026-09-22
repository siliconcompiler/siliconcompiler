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
