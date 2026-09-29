'''The client half of login, refresh and the edge, against the fake server.

What the v1 review changed about how a client authenticates: the OAuth error
shape at the two OAuth endpoints, nonces in both of their shapes, an access
layer in front of the API, redirects followed by hand, one refresh at a time
per store, the device grant's poll answers, and token exchange for CI.
'''
import base64
import json
import os
import stat
import sys

import pytest
import requests
import responses

from siliconcompiler.remote import Client, Credentials, RemoteError, ServerProblem
from siliconcompiler.remote.client import (
    GRANT_DEVICE_CODE, GRANT_TOKEN_EXCHANGE)
from siliconcompiler.remote.client.credentials import StoreError, parse_ci_secret
from siliconcompiler.remote.client.transport import EdgeRefused

from conftest import problem


def _form(body):
    from urllib.parse import parse_qs

    if isinstance(body, bytes):
        body = body.decode()
    return {k: v[0] for k, v in parse_qs(body).items()}


def _claims(token):
    import jwt

    return jwt.decode(token, options={"verify_signature": False})


def _posts(fake_v1, path="auth/token"):
    return [c.request for c in fake_v1.calls
            if c.request.method == "POST" and c.request.url.endswith(path)]


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    return slept


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


###########################
# Nonces, in both shapes
###########################

def test_a_nonce_asked_for_at_the_token_endpoint_is_sent_again(
        fake_v1, tmp_credentials, client_credentials):
    '''At an OAuth endpoint a nonce challenge is `use_dpop_nonce` in the OAuth
    shape, not a problem.'''
    fake_v1.route(responses.POST, "auth/token", {"error": "use_dpop_nonce"}, status=400,
                  headers={"DPoP-Nonce": "token-nonce"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    first, second = _posts(fake_v1)
    assert "nonce" not in _claims(first.headers["DPoP"])
    assert _claims(second.headers["DPoP"])["nonce"] == "token-nonce"


def test_a_nonce_asked_for_by_a_resource_is_sent_again(logged_in, fake_v1):
    '''Elsewhere it is the registry's `dpop-nonce-required`.'''
    fake_v1.route(responses.GET, "me", problem("dpop-nonce-required", 401), status=401,
                  content_type="application/problem+json",
                  headers={"DPoP-Nonce": "api-nonce"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert logged_in.me()["id"] == "u1"
    assert _claims(fake_v1.calls[-1].request.headers["DPoP"])["nonce"] == "api-nonce"


def test_a_nonce_is_kept_per_origin(logged_in, fake_v1):
    '''A nonce belongs to the origin that issued it.'''
    transport = logged_in.transport
    transport._nonces["https://elsewhere.test"] = "not-this-one"

    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"},
                  headers={"DPoP-Nonce": "this-one"})
    logged_in.me()

    assert transport._nonces["https://sc-server.test"] == "this-one"
    assert transport._nonces["https://elsewhere.test"] == "not-this-one"


###########################
# The OAuth shape
###########################

def test_a_problem_at_the_token_endpoint_is_read_as_a_problem(
        fake_v1, tmp_credentials, client_credentials, no_sleep):
    '''🔴 The Content-Type decides the shape: a 429 in problem+json at the
    token endpoint is a rate limit, waited out, never read for `error`.'''
    fake_v1.route(responses.POST, "auth/token", problem("rate-limited", 429),
                  status=429, content_type="application/problem+json",
                  headers={"Retry-After": "3"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    assert no_sleep == [3.0]
    assert len(_posts(fake_v1)) == 2


def test_a_key_bound_elsewhere_names_the_operator_command(
        fake_v1, tmp_credentials):
    '''`invalid_client` is not something retrying fixes.'''
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_client",
                   "error_description": "bound to a different key"}, status=401)

    with pytest.raises(RemoteError) as raised:
        Client(tmp_credentials).login()

    assert "release-binding" in str(raised.value)
    assert len(_posts(fake_v1)) == 1


def test_a_stale_grant_cache_is_refreshed_and_the_login_switches(
        fake_v1, tmp_credentials, capabilities, no_sleep):
    '''`unsupported_grant_type` is the only thing that says the cache is
    stale.'''
    tmp_credentials.update_session(grant_types_supported=["client_credentials"])
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "unsupported_grant_type"}, status=400)
    _offer(fake_v1, capabilities, GRANT_DEVICE_CODE, "refresh_token")
    fake_v1.route(responses.POST, "auth/device",
                  {"device_code": "dc", "user_code": "ABCD-EFGH",
                   "verification_uri": "https://sc-server.test/device",
                   "interval": 1, "expires_in": 600})
    fake_v1.route(responses.POST, "auth/token",
                  {"access_token": "a", "token_type": "DPoP", "expires_in": 900,
                   "refresh_token": "r"})

    Client(tmp_credentials).login()

    assert [_form(r.body)["grant_type"] for r in _posts(fake_v1)] == \
        ["client_credentials", GRANT_DEVICE_CODE]
    assert tmp_credentials.session_value("grant_types_supported") == \
        [GRANT_DEVICE_CODE, "refresh_token"]


###########################
# The edge
###########################

def test_an_html_refusal_is_the_edge_not_the_api(logged_in, fake_v1):
    fake_v1.route(responses.GET, "me", "<html><body>Forbidden</body></html>",
                  status=403, content_type="text/html")

    with pytest.raises(EdgeRefused) as raised:
        logged_in.me()

    assert "not the API" in str(raised.value)


def test_a_redirect_to_an_identity_provider_is_not_followed(logged_in, fake_v1):
    '''A 302 to a login page on /v1 is an access layer asking for a person.'''
    fake_v1.route(responses.GET, "me", "", status=302,
                  headers={"Location": "https://idp.example/login"})

    with pytest.raises(EdgeRefused):
        logged_in.me()

    assert not any("idp.example" in c.request.url for c in fake_v1.calls)


###########################
# Following a redirect by hand
###########################

def test_storage_on_another_origin_gets_no_credential_of_any_kind(
        logged_in, fake_v1, tmp_credentials, tmp_path):
    tmp_credentials.set_header("https://sc-server.test", "CF-Access-Client-Id", "id")
    tmp_credentials.set_header("https://storage.test", "X-Storage", "never-sent")

    fake_v1.route(responses.GET, "jobs/J/artifacts/A", "", status=303,
                  headers={"Location": "https://storage.test/object?sig=1"})
    fake_v1.elsewhere(responses.GET, "https://storage.test/object", "bytes",
                      content_type="application/octet-stream")

    logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")

    api, storage = fake_v1.calls[-2].request, fake_v1.calls[-1].request
    assert api.headers["CF-Access-Client-Id"] == "id"
    for name in ("Authorization", "DPoP", "CF-Access-Client-Id", "X-Storage"):
        assert name not in storage.headers


def test_a_stream_host_gets_only_the_headers_configured_for_it(
        logged_in, fake_v1, tmp_credentials):
    tmp_credentials.set_header("https://sc-server.test", "CF-Access-Client-Id", "id")
    tmp_credentials.set_header("https://stream.test", "X-Stream", "s")

    fake_v1.route(responses.GET, "jobs/J/logs", "", status=303,
                  headers={"Location": "https://stream.test/log"})
    fake_v1.elsewhere(responses.GET, "https://stream.test/log", "line\n",
                      content_type="text/plain")

    logged_in.follow_log("J", "syn", "0")

    stream = fake_v1.calls[-1].request
    assert stream.headers["X-Stream"] == "s"
    assert "CF-Access-Client-Id" not in stream.headers
    assert "Authorization" not in stream.headers


def test_https_is_never_followed_to_plain_http(logged_in, fake_v1, tmp_path):
    fake_v1.route(responses.GET, "jobs/J/artifacts/A", "", status=303,
                  headers={"Location": "http://storage.test/object"})

    with pytest.raises(RemoteError) as raised:
        logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")

    assert "plain http" in str(raised.value)


def test_a_header_value_with_a_line_break_is_refused(tmp_credentials):
    with pytest.raises(StoreError):
        tmp_credentials.set_header("https://sc-server.test", "X-A", "v\r\nX-B: w")
    with pytest.raises(StoreError):
        tmp_credentials.set_header("https://sc-server.test", "Authorization", "v")


def test_a_header_value_is_never_printed(tmp_credentials, fake_v1, caplog):
    tmp_credentials.set_header("https://sc-server.test", "CF-Access-Client-Secret",
                               "very-secret")

    with caplog.at_level("INFO"):
        Client(tmp_credentials).print_configuration()

    assert "CF-Access-Client-Secret" in caplog.text
    assert "very-secret" not in caplog.text


###########################
# One refresh at a time
###########################

def test_two_processes_refreshing_keep_the_session(fake_v1, tmp_credentials,
                                                   client_credentials):
    '''🔴 A process that waited for the lock uses what it finds in the store,
    never the token it held before: presenting a rotated one after the grace
    window would end every worker's session.'''
    tmp_credentials.update_session(refresh_token="r1")
    first = Client(Credentials(tmp_credentials.path))
    second = Client(Credentials(tmp_credentials.path))

    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r2"})
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r3"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    first.me()
    second.me()

    assert [_form(r.body)["refresh_token"] for r in _posts(fake_v1)] == ["r1", "r2"]
    assert Credentials(tmp_credentials.path).refresh_token == "r3"


def test_a_lost_refresh_is_retried_with_the_same_token(fake_v1, tmp_credentials,
                                                       client_credentials, no_sleep):
    '''The answer was lost, not the request: the server rotated, and the grace
    window gives the same pair back for the same token.'''
    tmp_credentials.update_session(refresh_token="r1")
    fake_v1._mock.add(responses.POST, fake_v1.url("auth/token"),
                      body=requests.ConnectionError("connection reset"))
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "refresh_token": "r2"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()

    assert [_form(r.body)["refresh_token"] for r in _posts(fake_v1)] == ["r1", "r1"]
    assert tmp_credentials.refresh_token == "r2"


def test_a_refresh_sends_no_scope(fake_v1, tmp_credentials, client_credentials):
    tmp_credentials.update_session(refresh_token="r1")
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()

    assert "scope" not in _form(_posts(fake_v1)[0].body)


###########################
# The store
###########################

@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
@pytest.mark.parametrize("which", ["dir", "key", "sessions"])
def test_a_store_others_can_read_stops_the_client(tmp_credentials, which):
    tmp_credentials.key()
    tmp_credentials.update_session(refresh_token="r1")
    target = {"dir": tmp_credentials.auth_dir,
              "key": tmp_credentials.key_path,
              "sessions": tmp_credentials.auth_dir / "sessions.json"}[which]
    os.chmod(target, stat.S_IMODE(os.stat(target).st_mode) | 0o044)

    with pytest.raises(StoreError) as raised:
        Credentials(tmp_credentials.path)

    assert "sc-remote -rotate_key" in str(raised.value)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
def test_the_store_is_written_private(tmp_credentials):
    tmp_credentials.key()
    tmp_credentials.update_session(refresh_token="r1")

    assert stat.S_IMODE(os.stat(tmp_credentials.auth_dir).st_mode) == 0o700
    for entry in tmp_credentials.auth_dir.iterdir():
        assert stat.S_IMODE(os.stat(entry).st_mode) & 0o077 == 0, entry


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
def test_the_store_is_private_from_creation_whatever_the_umask(tmp_path, monkeypatch):
    '''Each file created with its mode set, never `open()` then `chmod()`:
    a permissive umask opens no window.'''
    monkeypatch.delenv("SC_AUTH_DIR", raising=False)
    previous = os.umask(0)
    try:
        credentials = Credentials(tmp_path / "home" / ".sc" / "credentials")
        credentials.key()
        credentials.update_session(refresh_token="r1")
    finally:
        os.umask(previous)

    assert credentials.key_path == tmp_path / "home" / ".sc" / "auth" / "dpop-key.pem"
    assert stat.S_IMODE(os.stat(credentials.auth_dir).st_mode) == 0o700
    for entry in credentials.auth_dir.iterdir():
        assert stat.S_IMODE(os.stat(entry).st_mode) == 0o600, entry


def test_the_store_is_restricted_to_the_user_when_created_on_windows(tmp_path, monkeypatch):
    '''The Windows equivalent of 0700, applied as the directory is made:
    inheritance off, and full control to the user alone, inherited by every
    file created in it.'''
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


@pytest.mark.parametrize("refusal", [
    ("auth/token", {"error": "invalid_client"}, 401, "application/json"),
    ("auth/token", {"error": "invalid_dpop_proof"}, 400, "application/json"),
    ("me", problem("invalid-dpop-proof", 401), 401, "application/problem+json"),
])
def test_no_refusal_replaces_the_key(fake_v1, tmp_credentials, client_credentials, refusal):
    '''🔴 The key is the device pin: only `rotate_key` replaces it, and no
    authentication error does.'''
    path, body, status, content_type = refusal
    before = tmp_credentials.thumbprint
    stored = tmp_credentials.key_path.read_bytes()
    if path == "me":
        fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET if path == "me" else responses.POST, path, body,
                  status=status, content_type=content_type)
    fake_v1.route(responses.GET if path == "me" else responses.POST, path, body,
                  status=status, content_type=content_type)

    with pytest.raises(RemoteError):
        client = Client(tmp_credentials)
        client.me() if path == "me" else client.login()

    assert tmp_credentials.thumbprint == before
    assert tmp_credentials.key_path.read_bytes() == stored
    assert Credentials(tmp_credentials.path).thumbprint == before


def test_the_auth_dir_can_be_moved(monkeypatch, tmp_path):
    monkeypatch.setenv("SC_AUTH_DIR", str(tmp_path / "elsewhere"))
    creds = Credentials(tmp_path / "home" / "credentials")
    creds.key()

    assert creds.key_path.parent == tmp_path / "elsewhere"


###########################
# The device grant
###########################

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

    assert len(_posts(fake_v1, "auth/device")) == 2
    assert [_form(r.body)["device_code"] for r in _posts(fake_v1)] == ["first", "second"]


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


###########################
# Token exchange
###########################

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


def test_a_ci_credential_is_traded_before_any_user_code(fake_v1, tmp_credentials,
                                                        exchange):
    exchange()

    Client(tmp_credentials, open_browser=False).login()

    assert not _posts(fake_v1, "auth/device")
    (trade,) = _posts(fake_v1)
    form = _form(trade.body)
    assert form["grant_type"] == GRANT_TOKEN_EXCHANGE

    assertion = _claims(form["subject_token"])
    assert assertion["aud"] == "https://sc-server.test"
    assert assertion["exp"] - assertion["iat"] <= 300
    assert assertion["cnf"]["jkt"] == tmp_credentials.thumbprint
    assert assertion["iss"] == assertion["sub"] == "01J9credential"

    # No refresh token comes back, and none is written down.
    assert tmp_credentials.refresh_token is None


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
    assert [_form(r.body)["grant_type"] for r in _posts(fake_v1)] == \
        [GRANT_TOKEN_EXCHANGE, GRANT_TOKEN_EXCHANGE]
    assert fake_v1.calls[-1].request.headers["Authorization"] == "DPoP two"


def test_a_ci_credential_near_expiry_warns_the_pipeline(fake_v1, tmp_credentials,
                                                        exchange, monkeypatch,
                                                        capsys, caplog):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    exchange(session_expires_in=3 * 86400)

    Client(tmp_credentials, open_browser=False).login()

    assert "::warning::This CI credential expires in 3 days" in capsys.readouterr().out
    assert "expires in 3 days" in caplog.text


def test_a_ci_credential_is_never_sent_over_plain_http(tmp_path, monkeypatch, ci_secret):
    creds = Credentials(tmp_path / "credentials")
    creds.update(address="http://sc-server.test")
    creds.update_session(grant_types_supported=[GRANT_TOKEN_EXCHANGE])

    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        with pytest.raises(RemoteError) as raised:
            Client(creds, open_browser=False).login()
        assert not mock.calls

    assert "https" in str(raised.value)


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


def test_the_ci_secret_parses_with_underscores_in_the_key(ci_secret):
    credential_id, key = parse_ci_secret(ci_secret)

    assert credential_id == "01J9credential"
    assert key.curve.name == "secp256r1"


def test_ci_setup_writes_the_store_and_asks_for_the_access_headers(
        tmp_path, monkeypatch, ci_secret):
    '''The headers are typed in, never read from an environment variable of
    the client's choosing.'''
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

    creds = Credentials(tmp_path / "home" / "credentials")
    Client(creds).ci_setup(server="https://sc-server.test")

    exported = (tmp_path / "github_env").read_text()
    assert f"SC_AUTH_DIR={tmp_path / 'runner' / 'sc-auth'}" in exported
    assert "cf-secret" not in exported

    monkeypatch.setenv("SC_AUTH_DIR", str(tmp_path / "runner" / "sc-auth"))
    monkeypatch.delenv("SC_CI_CREDENTIAL")
    reopened = Credentials(tmp_path / "home" / "credentials")
    assert reopened.ci_secret() == ci_secret
    assert reopened.headers_for("https://sc-server.test") == {
        "CF-Access-Client-Id": "cf-id", "CF-Access-Client-Secret": "cf-secret"}
    assert json.loads(reopened.path.read_text())["address"].startswith("https://")


def test_ci_setup_without_a_terminal_asks_nothing(tmp_path, monkeypatch, ci_secret):
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "ignored")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "ignored")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    creds = Credentials(tmp_path / "home" / "credentials")
    Client(creds).ci_setup(server="https://sc-server.test")

    assert creds.headers_for("https://sc-server.test") == {}


def test_a_header_value_is_read_from_a_pipe(tmp_credentials, monkeypatch):
    '''How a pipeline sets one: `echo "$SECRET" | sc-remote -header NAME`.'''
    import io

    from siliconcompiler.remote.client import read_secret

    monkeypatch.setattr("sys.stdin", io.StringIO("piped-value\n"))

    assert read_secret("CF-Access-Client-Secret") == "piped-value"


def test_a_rotation_revokes_the_old_device_with_the_old_key(
        logged_in, fake_v1, tmp_credentials, client_credentials):
    '''The old key proves possession one last time, then the new key logs in.'''
    old = tmp_credentials.thumbprint
    fake_v1.route(responses.GET, "devices",
                  {"items": [{"id": "d-old", "name": "laptop", "current": True}]})
    fake_v1.route(responses.DELETE, "devices/d-old", "", status=204)
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    logged_in.rotate_key()

    import jwt

    from siliconcompiler.remote import dpop

    revoke, = [c.request for c in fake_v1.calls if c.request.method == "DELETE"]
    login = _posts(fake_v1)[-1]

    def signer(request):
        return dpop.jwk_thumbprint(jwt.get_unverified_header(request.headers["DPoP"])["jwk"])

    assert signer(revoke) == old
    assert signer(login) == tmp_credentials.thumbprint != old
    assert fake_v1.calls.index(next(c for c in fake_v1.calls if c.request is revoke)) < \
        fake_v1.calls.index(next(c for c in fake_v1.calls if c.request is login))


def test_a_rotation_the_server_cannot_hear_still_rotates(
        logged_in, fake_v1, tmp_credentials, client_credentials, caplog):
    old = tmp_credentials.thumbprint
    fake_v1.route(responses.GET, "devices", "<html>502</html>", status=502,
                  content_type="text/html")
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    logged_in.rotate_key()

    assert tmp_credentials.thumbprint != old
    assert "releases the binding" in caplog.text
