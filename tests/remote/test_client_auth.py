'''The client half of login, refresh, the store and the edge, against the
fake server.'''
import base64
import json
import os
import sys

import pytest
import requests
import responses

from siliconcompiler.remote import Client, Credentials, RemoteError, ServerProblem
from siliconcompiler.remote.client import (
    GRANT_CLIENT_CREDENTIALS, GRANT_DEVICE_CODE, GRANT_TOKEN_EXCHANGE, SCOPES, cli)
from siliconcompiler.remote.client.credentials import StoreError

from conftest import FakeV1, claims, form, grants, make_authority, mode, posts, problem


posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")


@pytest.fixture
def ci_secret(monkeypatch):
    '''A CI credential, as the portal would mint it.'''
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat)

    key = ec.generate_private_key(ec.SECP256R1())
    der = key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    secret = "scci_01J9credential_" + \
        base64.urlsafe_b64encode(der).decode().rstrip("=")
    monkeypatch.setenv("SC_CI_CREDENTIAL", secret)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    return secret


def _offer(fake_v1, capabilities, *grants):
    fake_v1.replace(responses.GET, "", {**capabilities,
                                        "grant_types_supported": list(grants)})


def test_a_nonce_is_kept_per_origin(logged_in, fake_v1):
    transport = logged_in.transport
    transport._nonces["https://elsewhere.test"] = "not-this-one"

    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"},
                  headers={"DPoP-Nonce": "this-one"})
    logged_in.me()

    assert transport._nonces["https://sc-server.test"] == "this-one"
    assert transport._nonces["https://elsewhere.test"] == "not-this-one"


def test_a_problem_at_the_token_endpoint_is_read_as_a_problem(
        fake_v1, tmp_credentials, client_credentials, no_sleep):
    '''The Content-Type decides the shape: a problem+json 429 is waited
    out, never read for `error`.'''
    fake_v1.route(responses.POST, "auth/token", problem("rate-limited", 429),
                  status=429, content_type="application/problem+json",
                  headers={"Retry-After": "3"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    assert no_sleep == [3.0]
    assert len(posts(fake_v1)) == 2


def test_a_key_bound_elsewhere_says_the_operator_can_release_it(fake_v1, tmp_credentials):
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_client",
                   "error_description": "bound to a different key"}, status=401)

    with pytest.raises(RemoteError) as raised:
        Client(tmp_credentials).login()

    assert "operator can release the binding" in str(raised.value)
    assert "registry" not in str(raised.value)
    assert len(posts(fake_v1)) == 1


def test_a_refused_grant_reads_the_offer_again_and_the_login_switches(
        fake_v1, tmp_credentials, capabilities, no_sleep):
    '''`unsupported_grant_type` says the offer changed: read again, cache nothing.'''
    _offer(fake_v1, capabilities, GRANT_CLIENT_CREDENTIALS)
    fake_v1.route(responses.GET, "", {**capabilities, "grant_types_supported":
                                      [GRANT_DEVICE_CODE, "refresh_token"]})
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "unsupported_grant_type"}, status=400)
    fake_v1.route(responses.POST, "auth/device",
                  {"device_code": "dc", "user_code": "ABCD-EFGH",
                   "verification_uri": "https://sc-server.test/device",
                   "interval": 1, "expires_in": 600})
    fake_v1.route(responses.POST, "auth/token",
                  {"access_token": "a", "token_type": "DPoP", "expires_in": 900,
                   "refresh_token": "r"})

    Client(tmp_credentials).login()

    assert grants(fake_v1) == ["client_credentials", GRANT_DEVICE_CODE]
    assert "grant_types_supported" not in tmp_credentials.path.read_text()


def test_the_login_prompt_shows_what_the_approval_page_shows(
        fake_v1, tmp_credentials, capabilities, no_sleep, monkeypatch, caplog):
    '''Beside the code, the machine key the server computes from this machine's
    proof, and the host it was told.'''
    import logging

    monkeypatch.setattr("platform.node", lambda: "fabric-ws-3")
    _offer(fake_v1, capabilities, GRANT_DEVICE_CODE, "refresh_token")
    fake_v1.route(responses.POST, "auth/device",
                  {"device_code": "dc", "user_code": "ABCD-EFGH",
                   "verification_uri": "https://sc-server.test/device",
                   "interval": 1, "expires_in": 600})
    fake_v1.route(responses.POST, "auth/token",
                  {"access_token": "a", "token_type": "DPoP", "expires_in": 900,
                   "refresh_token": "r"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).login()

    assert "enter the code ABCD-EFGH" in caplog.text
    assert f"Machine key: {tmp_credentials.thumbprint} " in caplog.text
    assert "This machine: fabric-ws-3" in caplog.text
    assert form(posts(fake_v1, "auth/device")[0].body)["requesting_host"] == "fabric-ws-3"


@pytest.mark.parametrize("location", [
    "https://storage.test/object?sig=1",
    "https://sc-server.test/storage/artifact/J/A?sig=1",
    "https://stream.test/log",
    "https://sc-server.test/v1/streams/abc",
], ids=["storage-elsewhere", "storage-same-origin", "stream-elsewhere",
        "stream-same-origin"])
def test_a_followed_redirect_gets_operator_headers_only_on_the_apis_origin(
        logged_in, fake_v1, tmp_path, location):
    '''Operator headers go to the API's origin, where an edge
    wants them, and nowhere else; no token or proof goes to either, since the
    signature is the credential.'''
    logged_in.set_header("CF-Access-Client-Id", "id")
    log = "/stream" in location or "/streams/" in location
    fake_v1.route(responses.GET, "jobs/J/logs" if log else "jobs/J/artifacts/A", "",
                  status=303, headers={"Location": location})
    fake_v1.elsewhere(responses.GET, location.split("?")[0], "line\n" if log else "bytes",
                      content_type="text/plain" if log else "application/octet-stream")

    if log:
        logged_in.follow_log("J", "syn", "0")
    else:
        logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")

    api, followed = fake_v1.calls[-2].request, fake_v1.calls[-1].request
    assert api.headers["CF-Access-Client-Id"] == "id"
    assert ("CF-Access-Client-Id" in followed.headers) == \
        location.startswith("https://sc-server.test/")
    assert "Authorization" not in followed.headers and "DPoP" not in followed.headers


@pytest.fixture
def netrc_everywhere(tmp_path, monkeypatch):
    '''A `~/.netrc` entry for the API's host, storage's and the stream's.'''
    netrc = tmp_path / "netrc"
    netrc.write_text("machine sc-server.test login alice password api-secret\n"
                     "machine storage.test login alice password storage-secret\n"
                     "machine stream.test login alice password stream-secret\n")
    netrc.chmod(0o600)
    monkeypatch.setenv("NETRC", str(netrc))
    return netrc


def test_no_request_carries_a_credential_from_netrc(
        logged_in, fake_v1, netrc_everywhere, tmp_path):
    '''Without the session's own `auth`, requests replaces `DPoP <token>`
    with the netrc login: every API request still carries DPoP, storage and
    the stream nothing, and no Basic credential goes anywhere.'''
    fake_v1.route(responses.GET, "me", {"user_id": "u"})
    fake_v1.route(responses.GET, "jobs/J/artifacts/A", "", status=303,
                  headers={"Location": "https://storage.test/object?sig=1"})
    fake_v1.elsewhere(responses.GET, "https://storage.test/object", "bytes",
                      content_type="application/octet-stream")
    fake_v1.route(responses.GET, "jobs/J/logs", "", status=303,
                  headers={"Location": "https://stream.test/log"})
    fake_v1.elsewhere(responses.GET, "https://stream.test/log", "line\n",
                      content_type="text/plain")

    logged_in.me()
    logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")
    logged_in.follow_log("J", "syn", "0")

    sent = [call.request for call in fake_v1.calls]
    assert not any("Basic" in (r.headers.get("Authorization") or "") for r in sent)
    for request in sent:
        if request.url.startswith("https://sc-server.test/v1/"):
            # A token's own endpoint carries a proof and no token.
            if not request.url.startswith("https://sc-server.test/v1/auth/"):
                assert request.headers["Authorization"].startswith("DPoP "), request.url
        else:
            assert "Authorization" not in request.headers, request.url


def test_the_environment_still_says_where_the_proxy_is(tmp_credentials, monkeypatch, tmp_path):
    '''Not `trust_env = False`, which would drop the proxy and CA bundle too.'''
    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.client.transport import Transport

    bundle = tmp_path / "ca.pem"
    bundle.write_text("")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.test:3128")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    transport = Transport("https://sc-server.test/v1", dpop.generate_key(), tmp_credentials, None)

    settings = transport._session.merge_environment_settings(
        "https://sc-server.test/v1/me", {}, None, None, None)

    assert transport._session.trust_env
    assert settings["proxies"]["https"] == "http://proxy.test:3128"
    assert settings["verify"] == str(bundle)


def test_requests_itself_follows_no_redirect(logged_in, fake_v1, netrc_everywhere,
                                             monkeypatch, tmp_path):
    '''requests' `rebuild_auth` rereads netrc for a redirect's target, so a
    redirect is followed by hand, once, and a second is not chased.'''
    asked = []
    real = requests.Session.send

    def send(self, request, **kwargs):
        asked.append(kwargs.get("allow_redirects", True))
        return real(self, request, **kwargs)

    monkeypatch.setattr(requests.Session, "send", send)
    fake_v1.route(responses.GET, "jobs/J/artifacts/A", "", status=303,
                  headers={"Location": "https://storage.test/object"})
    fake_v1.elsewhere(responses.GET, "https://storage.test/object", "", status=302,
                      headers={"Location": "https://elsewhere.test/object"})

    with pytest.raises(RemoteError):
        logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")

    assert asked and not any(asked)
    assert not any("elsewhere.test" in call.request.url for call in fake_v1.calls)
    assert not (tmp_path / "a.bin").exists()


@pytest.mark.parametrize("base,target,followed", [
    ("https://sc-server.test/v1", "http://storage.test/object", False),
    ("https://sc-server.test/v1", "ftp://storage.test/object", False),
    ("http://sc-server.test/v1", "file:///etc/passwd", False),
    ("http://sc-server.test/v1", "https://storage.test/object", True)],
    ids=["downgrade", "ftp", "file", "upgrade"])
def test_a_redirect_is_followed_only_to_https_from_https(base, target, followed,
                                                         tmp_credentials):
    '''An https answer sends the client only to
    https, an http one to either, and nothing else is followed.'''
    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.client.transport import Transport

    transport = Transport(base, dpop.generate_key(), tmp_credentials, None)
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.add(responses.GET, f"{base}/redirect", status=303,
                 headers={"Location": target})
        mock.add(responses.GET, "https://storage.test/object", body="bytes")
        response = transport._session.get(f"{base}/redirect", allow_redirects=False)

        if followed:
            answer = transport.follow(response)
            assert answer.status_code == 200 and answer.text == "bytes"
        else:
            with pytest.raises(RemoteError, match="sends a client only to https"):
                transport.follow(response)


def test_a_header_value_is_checked_and_never_printed(tmp_credentials, fake_v1, caplog):
    with pytest.raises(StoreError):
        tmp_credentials.set_header("X-A", "v\r\nX-B: w")
    with pytest.raises(StoreError):
        tmp_credentials.set_header("Authorization", "v")

    tmp_credentials.set_header("CF-Access-Client-Secret", "very-secret")
    with caplog.at_level("INFO"):
        cli.print_configuration(Client(tmp_credentials))

    assert "CF-Access-Client-Secret" in caplog.text
    assert "very-secret" not in caplog.text


def test_two_processes_refreshing_keep_the_session(fake_v1, tmp_credentials,
                                                   client_credentials):
    '''A process that waited for the lock uses what is in the store: a
    rotated token presented after the grace window ends every session.'''
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    first = Client(Credentials(tmp_credentials.path))
    second = Client(Credentials(tmp_credentials.path))

    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r2"})
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r3"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    first.me()
    second.me()

    assert [form(r.body)["refresh_token"] for r in posts(fake_v1)] == ["r1", "r2"]
    assert Credentials(tmp_credentials.path).refresh_token == "r3"


def test_threads_sharing_a_client_refresh_once(fake_v1, tmp_credentials, client_credentials):
    '''A thread that waited on another's refresh uses the token it got: no second
    refresh and no login, as a remote run's tail threads share one client.'''
    import threading
    import time

    tmp_credentials.save_tokens({"refresh_token": "r1"})
    client = Client(tmp_credentials)
    inside = threading.Event()

    def refreshed(request):
        inside.set()
        # The second thread asks while this refresh is still in flight.
        time.sleep(0.5)
        return 200, {}, json.dumps({**client_credentials, "refresh_token": "r2"})

    fake_v1._mock.add_callback(responses.POST, fake_v1.url("auth/token"), callback=refreshed,
                               content_type="application/json")

    first = threading.Thread(target=client.transport.renew)
    first.start()
    assert inside.wait(5)
    second = threading.Thread(target=client.transport.renew)
    second.start()
    first.join(10)
    second.join(10)

    assert grants(fake_v1) == ["refresh_token"]
    assert client.transport.access_token == "access-token-one"


def test_a_lost_refresh_is_retried_with_the_same_token(fake_v1, tmp_credentials,
                                                       client_credentials, no_sleep):
    '''The answer was lost, not the request: the grace window repeats it.'''
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    fake_v1._mock.add(responses.POST, fake_v1.url("auth/token"),
                      body=requests.ConnectionError("connection reset"))
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r2"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()

    assert [form(r.body)["refresh_token"] for r in posts(fake_v1)] == ["r1", "r1"]
    assert tmp_credentials.refresh_token == "r2"


@posix_only
def test_the_store_is_private_from_creation_whatever_the_umask_and_tightened_when_widened(
        tmp_path, monkeypatch):
    '''Each file created with its mode set, never `open()` then `chmod()`; the key in a
    file of its own, which a narrower mount can leave out. Saving over a file somebody
    widened fixes it.'''
    monkeypatch.delenv("SC_AUTH_DIR", raising=False)
    previous = os.umask(0)
    try:
        credentials = Credentials(tmp_path / "home" / ".sc" / "auth" / "remote.json")
        credentials.set_server("https://sc-server.test")
        credentials.key()
        credentials.save_tokens({"refresh_token": "r1"})
    finally:
        os.umask(previous)

    assert credentials.key_path == tmp_path / "home" / ".sc" / "auth" / "dpop-key.pem"
    assert mode(credentials.auth_dir) == 0o700
    for entry in credentials.auth_dir.iterdir():
        assert mode(entry) == 0o600, entry

    os.chmod(credentials.path, 0o644)
    credentials.save_tokens({"refresh_token": "r2"})

    assert mode(credentials.path) == 0o600


def test_the_store_is_restricted_to_the_user_when_created_on_windows(tmp_path, monkeypatch):
    '''The Windows 0700: inheritance off, full control to the user alone.'''
    import subprocess

    from siliconcompiler.remote.client import credentials as module

    ran = []
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: ran.append(command))
    monkeypatch.delenv("SC_AUTH_DIR", raising=False)

    credentials = Credentials(tmp_path / ".sc" / "credentials")
    credentials.key()

    (command,) = [entry for entry in ran if entry and entry[0] == "icacls"]
    assert command[1] == str(credentials.auth_dir)
    assert command[2:4] == ["/inheritance:r", "/grant:r"]
    assert command[4].endswith(":(OI)(CI)F")


def test_the_auth_dir_can_be_moved(monkeypatch, tmp_path):
    monkeypatch.setenv("SC_AUTH_DIR", str(tmp_path / "elsewhere"))
    creds = Credentials(tmp_path / "home" / "credentials")
    creds.key()

    assert creds.key_path.parent == tmp_path / "elsewhere"


def _store_file(credentials):
    return json.loads(credentials.path.read_text())


def test_the_store_is_one_versioned_file_of_two_categories(
        fake_v1, tmp_credentials, client_credentials):
    '''No access token, scope, login mode, grant list or key kept in it.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})
    Client(tmp_credentials).me()
    tmp_credentials.set_header("CF-Access-Client-Id", "id")
    tmp_credentials.set_directory_whitelist(["/proj"])

    assert _store_file(tmp_credentials) == {
        "store": {"version": 1, "server": "https://sc-server.test/v1",
                  "directory_whitelist": ["/proj"]},
        "servers": {"https://sc-server.test/v1": {
            "user_id": "u1", "refresh_token": "refresh-token-one",
            "headers": {"CF-Access-Client-Id": "id"}}}}
    assert tmp_credentials.path == tmp_credentials.auth_dir / "remote.json"
    assert sorted(entry.name for entry in tmp_credentials.auth_dir.iterdir()) == \
        ["dpop-key.pem", "remote.json", "remote.json.lock"]


def test_a_store_a_newer_client_wrote_is_refused_by_name(tmp_credentials):
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    written = _store_file(tmp_credentials)
    written["store"]["version"] = 2
    tmp_credentials.path.write_text(json.dumps(written))

    with pytest.raises(StoreError, match="newer SiliconCompiler"):
        Credentials(tmp_credentials.path)


def test_a_ci_credential_takes_the_place_of_a_refresh_token(tmp_credentials, ci_secret,
                                                            monkeypatch):
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    tmp_credentials.save_ci_secret(ci_secret)
    monkeypatch.delenv("SC_CI_CREDENTIAL")

    entry = _store_file(tmp_credentials)["servers"]["https://sc-server.test/v1"]
    assert entry == {"ci_credential": ci_secret}
    assert tmp_credentials.ci_secret() == ci_secret
    assert Client(tmp_credentials).ci_session


def test_rotating_the_key_ends_each_session_and_keeps_the_rest(
        tmp_credentials, ci_secret, monkeypatch):
    monkeypatch.delenv("SC_CI_CREDENTIAL")
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    tmp_credentials.set_user_id("u1")
    tmp_credentials.set_header("X-Edge", "v")
    tmp_credentials.set_server("https://ci.test")
    tmp_credentials.save_ci_secret(ci_secret)
    before = tmp_credentials.thumbprint

    tmp_credentials.rotate_key()

    servers = _store_file(tmp_credentials)["servers"]
    assert servers["https://sc-server.test/v1"] == {"user_id": "u1", "headers": {"X-Edge": "v"}}
    assert servers["https://ci.test/v1"] == {"ci_credential": ci_secret}
    assert tmp_credentials.thumbprint != before


def _legacy_home(tmp_path):
    '''A released client's configuration file.'''
    home = tmp_path / "home" / ".sc"
    home.mkdir(parents=True)
    (home / "credentials").write_text(json.dumps({
        "address": "https://sc-server.test", "port": 443, "username": "someone",
        "password": "hunter2", "directory_whitelist": ["/proj"]}))
    return home


@pytest.mark.parametrize("named", ["store", "old-file"])
def test_an_older_clients_file_is_moved_in_once(tmp_path, caplog, named):
    '''Server and whitelist moved, the old file removed, and its username and password not
    kept; naming the old file still finds the store, saying where to point it.'''
    home = _legacy_home(tmp_path)
    path = home / ("auth" if named == "store" else "") / ("remote.json" if named == "store"
                                                          else "credentials")

    first = Credentials(path)
    again = Credentials(path)

    assert _store_file(first)["store"] == {
        "version": 1, "server": "https://sc-server.test:443/v1",
        "directory_whitelist": ["/proj"]}
    assert "hunter2" not in first.path.read_text()
    assert not (home / "credentials").exists()
    assert sorted(entry.name for entry in (home / "auth").iterdir()) == \
        ["remote.json", "remote.json.lock"]
    assert first.path == again.path == home / "auth" / "remote.json"
    assert again.server == "https://sc-server.test:443/v1"
    assert ("point -credentials there" in caplog.text) is (named == "old-file")


@pytest.fixture
def device(fake_v1, capabilities):
    _offer(fake_v1, capabilities, GRANT_DEVICE_CODE, "refresh_token")

    def started(code="dc"):
        fake_v1.route(responses.POST, "auth/device",
                      {"device_code": code, "user_code": "ABCD-EFGH",
                       "verification_uri": "https://sc-server.test/device",
                       "interval": 2, "expires_in": 600})
    return started


def test_the_device_poll_waits_and_slows_down(fake_v1, tmp_credentials, device,
                                              client_credentials, no_sleep, caplog):
    device()
    fake_v1.route(responses.POST, "auth/token", {"error": "authorization_pending"},
                  status=400)
    fake_v1.route(responses.POST, "auth/token", {"error": "slow_down"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    with caplog.at_level("INFO"):
        Client(tmp_credentials, open_browser=False).login()

    assert no_sleep == [2, 2, 7]
    assert "ABCD-EFGH" in caplog.text
    assert tmp_credentials.refresh_token == "refresh-token-one"


def test_an_expired_device_code_starts_again(fake_v1, tmp_credentials, device,
                                             client_credentials, no_sleep):
    device("first")
    device("second")
    fake_v1.route(responses.POST, "auth/token", {"error": "expired_token"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials, open_browser=False).login()

    assert len(posts(fake_v1, "auth/device")) == 2
    assert [form(r.body)["device_code"] for r in posts(fake_v1)] == ["first", "second"]


@pytest.mark.parametrize("reason,said", [(None, "denied"), ("devices", "limit of devices")])
def test_a_denied_device_login_says_why(fake_v1, tmp_credentials, device, no_sleep,
                                        reason, said):
    device()
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "access_denied", **({"reason": reason} if reason else {})},
                  status=400)

    with pytest.raises(RemoteError) as raised:
        Client(tmp_credentials, open_browser=False).login()

    assert said in str(raised.value)


@pytest.mark.parametrize("grant", ["client_credentials", "device"])
def test_the_display_name_is_the_username(request, fake_v1, tmp_credentials,
                                          client_credentials, no_sleep, grant):
    '''`display_name` is the bare username; a device's label also names its host.'''
    import getpass
    import platform

    if grant == "device":
        request.getfixturevalue("device")()
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials, open_browser=False).login()

    if grant == "device":
        sent = form(posts(fake_v1, "auth/device")[0].body)
        assert sent["device_label"] == f"{getpass.getuser()}@{platform.node()}"
    else:
        assert form(posts(fake_v1)[0].body)["display_name"] == getpass.getuser()


@pytest.mark.parametrize("ci,scope,level", [
    (False, " ".join(SCOPES), None),
    (False, "jobs:read profile:read", "WARNING"),
    (True, "jobs:read jobs:write artifacts:read profile:read", "INFO"),
], ids=["all", "narrowed", "ci"])
def test_a_scope_not_granted_is_named_at_login(request, fake_v1, tmp_credentials,
                                               client_credentials, caplog, ci, scope, level):
    '''Every grant asks for every scope, and a server narrows silently, so the
    answer's `scope` is read back. A CI credential is narrow by design.'''
    if ci:
        request.getfixturevalue("exchange")
    fake_v1.route(responses.POST, "auth/token", {**client_credentials, "scope": scope})

    with caplog.at_level("INFO"):
        Client(tmp_credentials, open_browser=False).login()

    assert form(posts(fake_v1)[0].body)["scope"] == " ".join(SCOPES)
    said = [record for record in caplog.records if "not granted" in record.getMessage()]
    assert [record.levelname for record in said] == ([level] if level else [])
    if level == "WARNING":
        assert "not granted jobs:write, jobs:delete, artifacts:read, devices:read, " \
            "devices:write:" in said[0].getMessage()


@pytest.fixture
def exchange(fake_v1, capabilities, ci_secret):
    _offer(fake_v1, capabilities, GRANT_DEVICE_CODE, GRANT_TOKEN_EXCHANGE,
           "refresh_token")

    def traded(access="ci-access", session_expires_in=30 * 86400):
        fake_v1.route(responses.POST, "auth/token",
                      {"access_token": access, "token_type": "DPoP",
                       "expires_in": 900, "session_expires_in": session_expires_in,
                       "scope": "jobs:read jobs:write"})
    return traded


@pytest.mark.parametrize("offered", [None, (GRANT_DEVICE_CODE,)],
                         ids=["exchange-offered", "device-only"])
def test_a_ci_key_trades_first_and_never_prints_a_code(
        fake_v1, capabilities, tmp_credentials, exchange, capsys, offered):
    '''Token exchange first whatever is offered, never a
    `user_code` in a CI log, and no refresh token kept.'''
    exchange()
    if offered:
        _offer(fake_v1, capabilities, *offered)

    Client(tmp_credentials, open_browser=False).login()

    assert not posts(fake_v1, "auth/device")
    (trade,) = posts(fake_v1)
    sent = form(trade.body)
    assert sent["grant_type"] == GRANT_TOKEN_EXCHANGE
    assertion = claims(sent["subject_token"])
    assert assertion["aud"] == "https://sc-server.test"
    assert assertion["exp"] - assertion["iat"] <= 300
    assert assertion["cnf"]["jkt"] == tmp_credentials.thumbprint
    assert assertion["iss"] == assertion["sub"] == "01J9credential"
    assert tmp_credentials.refresh_token is None
    assert "code" not in capsys.readouterr().out.lower()


def test_a_ci_session_trades_again_for_each_access_token(fake_v1, tmp_credentials,
                                                         exchange):
    exchange("one")
    client = Client(tmp_credentials, open_browser=False)
    client.login()

    fake_v1.route(responses.GET, "me", problem("invalid-token", 401), status=401,
                  content_type="application/problem+json")
    exchange("two")
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert client.me()["id"] == "u1"
    assert grants(fake_v1) == [GRANT_TOKEN_EXCHANGE, GRANT_TOKEN_EXCHANGE]
    assert fake_v1.calls[-1].request.headers["Authorization"] == "DPoP two"


def test_a_ci_credential_near_expiry_warns_the_pipeline(fake_v1, tmp_credentials,
                                                        exchange, monkeypatch,
                                                        capsys, caplog):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    exchange(session_expires_in=3 * 86400)

    Client(tmp_credentials, open_browser=False).login()

    assert "::warning::This CI credential expires in 3 days" in capsys.readouterr().out
    assert "expires in 3 days" in caplog.text


@pytest.mark.parametrize("entry", ["login", "renew"])
def test_a_ci_key_re_reads_the_grants_once_before_it_fails(
        fake_v1, capabilities, tmp_credentials, ci_secret, capsys, entry):
    '''Never falling back to a refresh, `client_credentials` or the device grant,
    though this machine and deployment have all three, whether a login or a command asked.'''
    tmp_credentials.save_tokens({"refresh_token": "an-interactive-session"})
    _offer(fake_v1, capabilities, GRANT_CLIENT_CREDENTIALS, GRANT_DEVICE_CODE,
           "refresh_token")
    fake_v1.route(responses.POST, "auth/token", {"error": "unsupported_grant_type"},
                  status=400)

    with pytest.raises(RemoteError, match="no non-interactive login for a CI credential"):
        client = Client(tmp_credentials, open_browser=False)
        (client.login if entry == "login" else client.transport.renew)()

    assert grants(fake_v1) == [GRANT_TOKEN_EXCHANGE]
    assert not posts(fake_v1, "auth/device")
    assert len([c for c in fake_v1.calls if c.request.method == "GET"
                and c.request.url.rstrip("/").endswith("/v1")]) == 1
    assert "code" not in capsys.readouterr().out.lower()


def test_a_ci_key_trades_after_the_grants_say_it_now_can(
        fake_v1, capabilities, tmp_credentials, ci_secret):
    _offer(fake_v1, capabilities, GRANT_TOKEN_EXCHANGE)
    fake_v1.route(responses.POST, "auth/token", {"error": "unsupported_grant_type"},
                  status=400)
    fake_v1.route(responses.POST, "auth/token",
                  {"access_token": "ci", "token_type": "DPoP", "expires_in": 900})

    Client(tmp_credentials, open_browser=False).login()

    assert grants(fake_v1) == [GRANT_TOKEN_EXCHANGE, GRANT_TOKEN_EXCHANGE]


def test_a_trade_refused_for_the_clock_is_minted_again_on_the_corrected_one(
        fake_v1, tmp_credentials, exchange):
    '''The assertion's time claims ride on the proof's clock, so the one retry
    carries a fresh assertion, with a new `jti`.'''
    import email.utils
    import time

    ahead = 600
    fake_v1.route(responses.POST, "auth/token", {"error": "invalid_dpop_proof"}, status=400,
                  headers={"Date": email.utils.formatdate(time.time() + ahead, usegmt=True)})
    exchange()

    Client(tmp_credentials, open_browser=False).login()

    first, second = (form(r.body)["subject_token"] for r in posts(fake_v1))
    first, second = claims(first), claims(second)
    assert first["jti"] != second["jti"]
    assert abs(second["iat"] - first["iat"] - ahead) <= 5
    assert second["exp"] - second["iat"] == 300
    assert abs(claims(posts(fake_v1)[1].headers["DPoP"])["iat"] - second["iat"]) <= 1


def test_insecure_transport_stops_and_is_never_sent_again(logged_in, fake_v1):
    '''Never switch scheme, which would hide a mistyped address.'''
    fake_v1.route(responses.GET, "me", problem("insecure-transport", 426), status=426,
                  content_type="application/problem+json", headers={"Upgrade": "TLS/1.2"})

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert "must be https" in str(raised.value)
    assert len([c for c in fake_v1.calls if c.request.url.endswith("/v1/me")]) == 1
    assert all(c.request.url.startswith("https://sc-server.test") for c in fake_v1.calls)


def test_a_ci_credential_is_never_sent_over_plain_http(tmp_path, ci_secret):
    creds = Credentials(tmp_path / "auth" / "remote.json")
    creds.set_server("http://sc-server.test")

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        with pytest.raises(RemoteError) as raised:
            Client(creds, open_browser=False).login()
        assert not mock.calls

    assert "https" in str(raised.value)


@pytest.fixture
def plain(capabilities, tmp_credentials):
    '''A deployment served over plain http, as a local sc-server is, and a client for it.'''
    tmp_credentials.set_server("http://sc-server.test")
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        server = FakeV1(mock, "http://sc-server.test/v1")
        server.route(responses.GET, "", capabilities)
        yield server, Client(tmp_credentials, open_browser=False)


@pytest.mark.parametrize("offered,sent", [
    ((GRANT_CLIENT_CREDENTIALS, "refresh_token"), True),
    ((GRANT_DEVICE_CODE, "refresh_token"), False),
    ((GRANT_CLIENT_CREDENTIALS, GRANT_DEVICE_CODE), False),
], ids=["sc-server", "device", "both"])
@pytest.mark.parametrize("held", [False, True], ids=["login", "refresh"])
def test_plain_http_carries_a_credential_only_where_nobody_is_authenticated(
        plain, capabilities, client_credentials, offered, sent, held):
    '''`GET /v1` decides before a login or a refresh token goes over http: a
    deployment that authenticates gets neither.'''
    server, client = plain
    _offer(server, capabilities, *offered)
    if held:
        client.credentials.save_tokens({"refresh_token": "r1"})
    server.route(responses.POST, "auth/token", client_credentials)

    if sent:
        client.transport.renew()
        assert grants(server) == ["refresh_token" if held else GRANT_CLIENT_CREDENTIALS]
    else:
        with pytest.raises(RemoteError, match="is not https"):
            client.transport.renew()
        assert not [call for call in server.calls if call.request.method == "POST"]


def test_a_grant_refused_over_plain_http_stops_the_login(plain, capabilities):
    '''No fallback to the device grant: a deployment offering it authenticates,
    so no code is asked for over http.'''
    server, client = plain
    server.route(responses.POST, "auth/token", {"error": "unsupported_grant_type"},
                 status=400)
    server.route(responses.GET, "", {**capabilities, "grant_types_supported":
                                     [GRANT_DEVICE_CODE, "refresh_token"]})

    with pytest.raises(RemoteError, match="is not https"):
        client.login()

    assert grants(server) == [GRANT_CLIENT_CREDENTIALS]
    assert not posts(server, "auth/device")


def test_a_project_bound_ci_credential_explains_a_404(fake_v1, tmp_credentials,
                                                      exchange):
    exchange()
    client = Client(tmp_credentials, open_browser=False)
    client.login()

    fake_v1.route(responses.GET, "jobs/J", problem("not-found", 404), status=404,
                  content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        client.job("J")

    assert "another project" in str(raised.value)


def test_ci_setup_writes_the_store_and_asks_for_the_access_headers(
        tmp_path, monkeypatch, ci_secret):
    '''Headers are typed in, never read from an environment variable.'''
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path / "runner"))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "github_env"))
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "ignored")
    monkeypatch.delenv("SC_AUTH_DIR", raising=False)

    answers = iter(["CF-Access-Client-Id", "CF-Access-Client-Secret", ""])
    values = iter(["cf-id", "cf-secret"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _: next(values))

    creds = Credentials(tmp_path / "home" / "auth" / "remote.json")
    Client(creds).ci_setup(server="https://sc-server.test")

    exported = (tmp_path / "github_env").read_text()
    assert f"SC_AUTH_DIR={tmp_path / 'runner' / 'sc-auth'}" in exported
    assert "cf-secret" not in exported

    monkeypatch.setenv("SC_AUTH_DIR", str(tmp_path / "runner" / "sc-auth"))
    monkeypatch.delenv("SC_CI_CREDENTIAL")
    reopened = Credentials(tmp_path / "home" / "auth" / "remote.json")
    assert reopened.ci_secret() == ci_secret
    assert reopened.headers() == {
        "CF-Access-Client-Id": "cf-id", "CF-Access-Client-Secret": "cf-secret"}
    assert reopened.server == "https://sc-server.test/v1"
    assert reopened.refresh_token is None


def test_ci_setup_without_a_terminal_asks_nothing(tmp_path, monkeypatch, ci_secret):
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "ignored")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "ignored")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    creds = Credentials(tmp_path / "home" / "auth" / "remote.json")
    Client(creds).ci_setup(server="https://sc-server.test")

    assert creds.headers() == {}


def test_a_rotation_revokes_the_old_device_with_the_old_key(
        logged_in, fake_v1, tmp_credentials, client_credentials):
    '''The old key proves possession one last time, then the new key logs in.'''
    import jwt

    from siliconcompiler.remote import dpop

    old = tmp_credentials.thumbprint
    fake_v1.route(responses.GET, "devices",
                  {"items": [{"id": "d-old", "name": "laptop", "current": True}]})
    fake_v1.route(responses.DELETE, "devices/d-old", "", status=204)
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    logged_in.rotate_key()

    sent = [c.request for c in fake_v1.calls]
    revoke, = [r for r in sent if r.method == "DELETE"]
    login = posts(fake_v1)[-1]

    def signer(request):
        return dpop.jwk_thumbprint(jwt.get_unverified_header(request.headers["DPoP"])["jwk"])

    assert signer(revoke) == old
    assert signer(login) == tmp_credentials.thumbprint != old
    assert sent.index(revoke) < sent.index(login)


@pytest.mark.parametrize("silence", ["bad-gateway", "timeout"])
def test_a_rotation_the_server_cannot_hear_still_rotates(
        logged_in, fake_v1, tmp_credentials, client_credentials, caplog, no_sleep, silence):
    old = tmp_credentials.thumbprint
    if silence == "timeout":
        fake_v1._mock.add(responses.GET, fake_v1.url("devices"), body=requests.Timeout())
    else:
        fake_v1.route(responses.GET, "devices", "<html>502</html>", status=502,
                      content_type="text/html")
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    logged_in.rotate_key()

    assert tmp_credentials.thumbprint != old
    assert "releases the binding" in caplog.text


@pytest.fixture
def tls_server(capabilities, client_credentials, monkeypatch):
    '''A v1 server over real TLS on this machine, its certificate signed by an
    authority of its own; yields its address and that authority's file.'''
    import http.server
    import ssl
    import threading
    from pathlib import Path

    for name in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")

    directory = Path("tls")
    directory.mkdir()
    authority, certificate, key = make_authority(directory)
    answers = {("GET", "/v1"): capabilities, ("POST", "/v1/auth/token"): client_credentials,
               ("GET", "/v1/me"): {"id": "u1", "issuer": "local"}}

    class Handler(http.server.BaseHTTPRequestHandler):
        def answer(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = answers.get((self.command, self.path.split("?")[0]))
            payload = json.dumps(body or {}).encode()
            self.send_response(200 if body is not None else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = answer

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(certificate), str(key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"https://127.0.0.1:{server.server_address[1]}", authority
    finally:
        server.shutdown()
        server.server_close()


def _store():
    from pathlib import Path

    return Credentials(Path("sc-home/auth/remote.json"))


def test_an_imported_authority_is_kept_privately_and_its_fingerprint_said(tmp_path):
    '''Re-importing the same file is harmless; another under its name is refused
    unless overwritten, which also rebuilds its trust bundle.'''
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    authority, certificate, _ = make_authority(tmp_path)
    store = _store()

    name, found = store.import_certificate(authority)

    expected = x509.load_pem_x509_certificate(authority.read_bytes())
    assert (name, store.certificates()) == ("our-ca", ["our-ca"])
    assert found == [("CN=Our CA", expected.fingerprint(hashes.SHA256()).hex(":").upper())]
    assert store.import_certificate(authority)[0] == "our-ca"
    if sys.platform != "win32":
        assert mode(store.certs_dir) == 0o700
        assert mode(store.certificate_path("our-ca")) == 0o600
    renamed = tmp_path / "elsewhere" / "our-ca.pem"
    renamed.parent.mkdir()
    renamed.write_bytes(certificate.read_bytes())
    store.trust_bundle("our-ca")
    with pytest.raises(StoreError, match="already imported as our-ca"):
        store.import_certificate(renamed)
    assert store.import_certificate(renamed, overwrite=True)[0] == "our-ca"
    assert store.certificate_path("our-ca").read_bytes() == certificate.read_bytes()
    assert store.trust_bundle("our-ca").read_bytes().endswith(certificate.read_bytes())
    (tmp_path / "notes.pem").write_text("not a certificate")
    with pytest.raises(StoreError, match="no PEM certificate"):
        store.import_certificate(tmp_path / "notes.pem")


def test_configure_offers_an_imported_authority_and_keeps_the_choice(tls_server, monkeypatch):
    '''Asked once, in -configure; every later command verifies with the choice.'''
    url, authority = tls_server
    store = _store()
    store.import_certificate(authority)
    asked = []
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("siliconcompiler.remote.client._ask",
                        lambda question, hint=None: asked.append(question) or "1")

    Client(store).configure_server(server=url)

    assert (store.server, store.certificate) == (f"{url}/v1", "our-ca")
    assert len(asked) == 1
    monkeypatch.setattr("siliconcompiler.remote.client._ask",
                        lambda *args, **kwargs: pytest.fail("asked again"))
    assert Client(store).me()["id"] == "u1"


@pytest.mark.parametrize("imported,terminal,answer", [
    (False, True, "1"), (True, False, "1"), (True, True, ""),
], ids=["nothing-imported", "no-terminal", "declined"])
def test_an_unverified_certificate_is_said_and_nothing_saved(tls_server, monkeypatch,
                                                             imported, terminal, answer):
    '''The failure names -import_cert; the client never trusts what the server
    presents, and a server it could not verify is not saved.'''
    from siliconcompiler.remote.client.transport import CertificateRefused

    url, authority = tls_server
    store = _store()
    if imported:
        store.import_certificate(authority)
    monkeypatch.setattr("sys.stdin.isatty", lambda: terminal)
    monkeypatch.setattr("siliconcompiler.remote.client._ask", lambda *args, **kwargs: answer)

    with pytest.raises(CertificateRefused, match="sc-config remote import-cert"):
        Client(store).configure_server(server=url)

    assert (store.server, store.certificate) == (None, None)


def test_only_configure_asks_whichmake_authority(tls_server, monkeypatch):
    '''Any other command fails and says to configure; a submit never stops for a question.'''
    from siliconcompiler.remote.client.transport import CertificateRefused

    url, authority = tls_server
    store = _store()
    store.import_certificate(authority)
    store.set_server(url)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("siliconcompiler.remote.client._ask",
                        lambda *args, **kwargs: pytest.fail("asked outside -configure"))

    with pytest.raises(CertificateRefused, match="sc-config remote configure"):
        Client(store).capabilities()


def test_an_imported_authority_is_trusted_beside_the_usual_ones(tmp_path, monkeypatch):
    '''Added to, never in place of, so public storage still verifies; a
    REQUESTS_CA_BUNDLE in the environment still wins.'''
    from requests.utils import DEFAULT_CA_BUNDLE_PATH

    authority, _, _ = make_authority(tmp_path)
    store = _store()
    store.import_certificate(authority)
    store.set_server("https://ours.test")
    store.set_certificate("our-ca")

    client = Client(store)
    bundle = store.trust_bundle("our-ca").read_bytes()
    session = client.transport._session

    assert open(DEFAULT_CA_BUNDLE_PATH, "rb").read().strip() in bundle
    assert authority.read_bytes().strip() in bundle
    assert session.verify == str(store.trust_bundle("our-ca"))
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(authority))
    assert session.merge_environment_settings(
        client.base_url, {}, None, None, None)["verify"] == str(authority)


@posix_only
@pytest.mark.parametrize("which,widen,match", [
    ("dir", 0o044, "sc-config remote rotate-key"),
    ("key", 0o044, "sc-config remote rotate-key"),
    ("store", 0o044, "sc-config remote rotate-key"),
    ("certificate", 0o666, None),
    ("fresh-directory", 0o755, "readable by others"),
])
def test_a_store_others_can_read_or_change_stops_the_client(tmp_path, which, widen, match):
    '''The directory holds the key: one others can read is refused, the key, store and
    imported authorities likewise, and only the store's own files are judged.'''
    if which == "fresh-directory":
        home = tmp_path / "mine"
        home.mkdir(mode=0o700)
        (home / "notes.txt").write_text("not the store's\n")
        os.chmod(home / "notes.txt", 0o644)
        shared = tmp_path / "shared"
        shared.mkdir()
        os.chmod(shared, widen)
        Credentials(home / "remote.json").set_server("https://sc-server.test")
        path = shared / "remote.json"
    else:
        authority, _, _ = make_authority(tmp_path)
        store = _store()
        store.set_server("https://sc-server.test")
        store.key()
        store.save_tokens({"refresh_token": "r1"})
        store.import_certificate(authority)
        target = {"dir": store.auth_dir, "key": store.key_path, "store": store.path,
                  "certificate": store.certificate_path("our-ca")}[which]
        os.chmod(target, mode(target) | widen)
        path = store.path

    with pytest.raises(StoreError, match=match):
        Credentials(path)
