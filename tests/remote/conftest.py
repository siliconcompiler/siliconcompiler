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
