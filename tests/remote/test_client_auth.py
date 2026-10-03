'''The client half of login, refresh, the store and the edge, against the
fake server.'''
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
    GRANT_CLIENT_CREDENTIALS, GRANT_DEVICE_CODE, GRANT_TOKEN_EXCHANGE)
from siliconcompiler.remote.client.credentials import StoreError, parse_ci_secret
from siliconcompiler.remote.client.transport import EdgeRefused

from conftest import problem


posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")


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


def _grants(fake_v1):
    return [_form(r.body)["grant_type"] for r in _posts(fake_v1)]


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


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


def test_a_nonce_asked_for_at_the_token_endpoint_is_sent_again(
        fake_v1, tmp_credentials, client_credentials):
    '''At an OAuth endpoint it is `use_dpop_nonce` in the OAuth shape.'''
    fake_v1.route(responses.POST, "auth/token", {"error": "use_dpop_nonce"}, status=400,
                  headers={"DPoP-Nonce": "token-nonce"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    first, second = _posts(fake_v1)
    assert "nonce" not in _claims(first.headers["DPoP"])
    assert _claims(second.headers["DPoP"])["nonce"] == "token-nonce"


@pytest.mark.parametrize("slug,challenge", [
    ("dpop-nonce-required", None),
    ("invalid-dpop-proof", 'DPoP error="use_dpop_nonce"'),
], ids=["registry-slug", "www-authenticate"])
def test_a_nonce_asked_for_by_a_resource_is_retried_not_refreshed(logged_in, fake_v1,
                                                                  slug, challenge):
    '''A client that only refreshes loops here for ever.'''
    headers = {"DPoP-Nonce": "api-nonce"}
    if challenge:
        headers["WWW-Authenticate"] = challenge
    fake_v1.route(responses.GET, "me", problem(slug, 401), status=401,
                  content_type="application/problem+json", headers=headers)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert logged_in.me()["id"] == "u1"
    assert _claims(fake_v1.calls[-1].request.headers["DPoP"])["nonce"] == "api-nonce"
    assert len(_posts(fake_v1)) == 1


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
    '''🔴 The Content-Type decides the shape: a problem+json 429 is waited
    out, never read for `error`.'''
    fake_v1.route(responses.POST, "auth/token", problem("rate-limited", 429),
                  status=429, content_type="application/problem+json",
                  headers={"Retry-After": "3"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    assert no_sleep == [3.0]
    assert len(_posts(fake_v1)) == 2


def test_a_key_bound_elsewhere_names_the_operator_command(fake_v1, tmp_credentials):
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_client",
                   "error_description": "bound to a different key"}, status=401)

    with pytest.raises(RemoteError) as raised:
        Client(tmp_credentials).login()

    assert "release-binding" in str(raised.value)
    assert len(_posts(fake_v1)) == 1


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

    assert _grants(fake_v1) == ["client_credentials", GRANT_DEVICE_CODE]
    assert "grant_types_supported" not in tmp_credentials.path.read_text()


@pytest.mark.parametrize("body,status,headers", [
    ("<html><body>Forbidden</body></html>", 403, None),
    ("", 302, {"Location": "https://idp.example/login"}),
], ids=["html", "idp-redirect"])
def test_an_access_layer_refusal_is_the_edge_not_the_api(logged_in, fake_v1, body, status,
                                                         headers):
    '''A 302 to a login page is an access layer asking for a person: not followed.'''
    fake_v1.route(responses.GET, "me", body, status=status, content_type="text/html",
                  headers=headers)

    with pytest.raises(EdgeRefused) as raised:
        logged_in.me()

    assert "not the API" in str(raised.value)
    assert not any("idp.example" in c.request.url for c in fake_v1.calls)


@pytest.mark.parametrize("location", [
    "https://storage.test/object?sig=1",
    "https://sc-server.test/storage/artifact/J/A?sig=1",
    "https://stream.test/log",
    "https://sc-server.test/v1/streams/abc",
], ids=["storage-elsewhere", "storage-same-origin", "stream-elsewhere",
        "stream-same-origin"])
def test_a_followed_redirect_gets_operator_headers_only_on_the_apis_origin(
        logged_in, fake_v1, tmp_path, location):
    '''🔴 Surface D304: operator headers go to the API's origin, where an edge
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
    '''🔴 Without the session's own `auth`, requests replaces `DPoP <token>`
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
    transport = Transport("https://sc-server.test/v1", dpop.generate_key(), tmp_credentials)

    settings = transport._session.merge_environment_settings(
        "https://sc-server.test/v1/me", {}, None, None, None)

    assert transport._session.trust_env
    assert settings["proxies"]["https"] == "http://proxy.test:3128"
    assert settings["verify"] == str(bundle)


def test_requests_itself_follows_no_redirect(logged_in, fake_v1, netrc_everywhere,
                                             monkeypatch, tmp_path):
    '''🔴 requests' `rebuild_auth` rereads netrc for a redirect's target, so a
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
    '''🔴 Contract rule 5 (D70): an https answer sends the client only to
    https, an http one to either, and nothing else is followed.'''
    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.client.transport import Transport

    transport = Transport(base, dpop.generate_key(), tmp_credentials)
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
        Client(tmp_credentials).print_configuration()

    assert "CF-Access-Client-Secret" in caplog.text
    assert "very-secret" not in caplog.text


def test_a_header_value_is_read_from_a_pipe(monkeypatch):
    '''`echo "$SECRET" | sc-remote -header NAME`.'''
    import io

    from siliconcompiler.remote.client import read_secret

    monkeypatch.setattr("sys.stdin", io.StringIO("piped-value\n"))

    assert read_secret("CF-Access-Client-Secret") == "piped-value"


def test_two_processes_refreshing_keep_the_session(fake_v1, tmp_credentials,
                                                   client_credentials):
    '''🔴 A process that waited for the lock uses what is in the store: a
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

    assert [_form(r.body)["refresh_token"] for r in _posts(fake_v1)] == ["r1", "r2"]
    assert Credentials(tmp_credentials.path).refresh_token == "r3"


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

    assert [_form(r.body)["refresh_token"] for r in _posts(fake_v1)] == ["r1", "r1"]
    assert tmp_credentials.refresh_token == "r2"


@posix_only
@pytest.mark.parametrize("which", ["dir", "key", "store"])
def test_a_store_others_can_read_stops_the_client(tmp_credentials, which):
    tmp_credentials.key()
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    target = {"dir": tmp_credentials.auth_dir,
              "key": tmp_credentials.key_path,
              "store": tmp_credentials.path}[which]
    os.chmod(target, _mode(target) | 0o044)

    with pytest.raises(StoreError) as raised:
        Credentials(tmp_credentials.path)

    assert "sc-remote -rotate_key" in str(raised.value)


@posix_only
def test_the_store_is_private_from_creation_whatever_the_umask(tmp_path, monkeypatch):
    '''Each file created with its mode set, never `open()` then `chmod()`;
    the key in a file of its own, which a narrower mount can leave out.'''
    monkeypatch.delenv("SC_AUTH_DIR", raising=False)
    previous = os.umask(0)
    try:
        credentials = Credentials(tmp_path / "home" / ".sc" / "auth" / "remote.json")
        credentials.key()
        credentials.save_tokens({"refresh_token": "r1"})
    finally:
        os.umask(previous)

    assert credentials.key_path == tmp_path / "home" / ".sc" / "auth" / "dpop-key.pem"
    assert _mode(credentials.auth_dir) == 0o700
    for entry in credentials.auth_dir.iterdir():
        assert _mode(entry) == 0o600, entry


@posix_only
def test_an_existing_wider_file_is_tightened(tmp_credentials):
    '''Re-running configure over a file somebody widened fixes it.'''
    tmp_credentials.save_tokens({"refresh_token": "secret"})
    os.chmod(tmp_credentials.path, 0o644)

    tmp_credentials.save_tokens({"refresh_token": "secret-again"})

    assert _mode(tmp_credentials.path) == 0o600


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


@pytest.mark.parametrize("path,body,status,content_type", [
    ("auth/token", {"error": "invalid_client"}, 401, "application/json"),
    ("auth/token", {"error": "invalid_dpop_proof"}, 400, "application/json"),
    ("me", problem("invalid-dpop-proof", 401), 401, "application/problem+json"),
])
def test_no_refusal_replaces_the_key(fake_v1, tmp_credentials, client_credentials, path,
                                     body, status, content_type):
    '''🔴 The key is the device pin: only `rotate_key` replaces it.'''
    before = tmp_credentials.thumbprint
    stored = tmp_credentials.key_path.read_bytes()
    method = responses.GET if path == "me" else responses.POST
    if path == "me":
        fake_v1.route(responses.POST, "auth/token", client_credentials)
    for _ in range(2):
        fake_v1.route(method, path, body, status=status, content_type=content_type)

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


def test_each_server_keeps_its_own_entry(tmp_credentials):
    '''One server's session and id are never read as another's.'''
    tmp_credentials.save_tokens({"refresh_token": "first"})
    tmp_credentials.set_user_id("me-on-first")
    tmp_credentials.set_server("https://other.test")
    assert (tmp_credentials.refresh_token, tmp_credentials.user_id) == (None, None)
    tmp_credentials.save_tokens({"refresh_token": "second"})

    tmp_credentials.set_server("https://sc-server.test")

    assert (tmp_credentials.refresh_token, tmp_credentials.user_id) == \
        ("first", "me-on-first")


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


def test_a_store_directory_is_private_or_refused(tmp_path):
    '''It holds the key: a working directory others can read is refused,
    and only the directory and the store's own files are judged.'''
    home = tmp_path / "mine"
    home.mkdir(mode=0o700)
    (home / "notes.txt").write_text("not the store's\n")
    os.chmod(home / "notes.txt", 0o644)
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)

    store = Credentials(home / "remote.json")
    store.set_server("https://sc-server.test")

    assert store.server == "https://sc-server.test/v1"
    with pytest.raises(StoreError, match="readable by others"):
        Credentials(shared / "remote.json")


def _legacy_home(tmp_path):
    '''A released client's configuration file.'''
    home = tmp_path / "home" / ".sc"
    home.mkdir(parents=True)
    (home / "credentials").write_text(json.dumps({
        "address": "https://sc-server.test", "port": 443, "username": "someone",
        "password": "hunter2", "directory_whitelist": ["/proj"]}))
    return home


def test_an_older_clients_file_is_moved_in_once(tmp_path):
    '''🔴 Server and whitelist moved, the old file removed, and its username
    and password not kept.'''
    home = _legacy_home(tmp_path)

    store = Credentials(home / "auth" / "remote.json")

    assert _store_file(store)["store"] == {
        "version": 1, "server": "https://sc-server.test:443/v1",
        "directory_whitelist": ["/proj"]}
    assert "hunter2" not in store.path.read_text()
    assert not (home / "credentials").exists()
    assert sorted(entry.name for entry in (home / "auth").iterdir()) == \
        ["remote.json", "remote.json.lock"]


def test_credentials_naming_an_older_file_finds_the_store_it_moved_to(tmp_path, caplog):
    '''`-credentials ~/.sc/credentials` still works, saying where to point it.'''
    home = _legacy_home(tmp_path)

    first = Credentials(home / "credentials")
    again = Credentials(home / "credentials")

    assert first.path == again.path == home / "auth" / "remote.json"
    assert again.server == "https://sc-server.test:443/v1"
    assert "point -credentials there" in caplog.text


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
    '''🔴 Identity §2: token exchange first whatever is offered, never a
    `user_code` in a CI log, and no refresh token kept.'''
    exchange()
    if offered:
        _offer(fake_v1, capabilities, *offered)

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
    assert _grants(fake_v1) == [GRANT_TOKEN_EXCHANGE, GRANT_TOKEN_EXCHANGE]
    assert fake_v1.calls[-1].request.headers["Authorization"] == "DPoP two"


def test_a_ci_credential_near_expiry_warns_the_pipeline(fake_v1, tmp_credentials,
                                                        exchange, monkeypatch,
                                                        capsys, caplog):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    exchange(session_expires_in=3 * 86400)

    Client(tmp_credentials, open_browser=False).login()

    assert "::warning::This CI credential expires in 3 days" in capsys.readouterr().out
    assert "expires in 3 days" in caplog.text


def test_a_ci_key_re_reads_the_grants_once_before_it_fails(
        fake_v1, capabilities, tmp_credentials, ci_secret, capsys):
    '''Never falling back to `client_credentials` or the device grant,
    though this deployment offers both.'''
    _offer(fake_v1, capabilities, GRANT_CLIENT_CREDENTIALS, GRANT_DEVICE_CODE,
           "refresh_token")
    fake_v1.route(responses.POST, "auth/token", {"error": "unsupported_grant_type"},
                  status=400)

    with pytest.raises(RemoteError, match="no non-interactive login for a CI credential"):
        Client(tmp_credentials, open_browser=False).login()

    assert _grants(fake_v1) == [GRANT_TOKEN_EXCHANGE]
    assert not _posts(fake_v1, "auth/device")
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

    assert _grants(fake_v1) == [GRANT_TOKEN_EXCHANGE, GRANT_TOKEN_EXCHANGE]


def test_insecure_transport_stops_and_is_never_sent_again(logged_in, fake_v1):
    '''Contract rule 5: never switch scheme, which would hide a mistyped address.'''
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
    login = _posts(fake_v1)[-1]

    def signer(request):
        return dpop.jwk_thumbprint(jwt.get_unverified_header(request.headers["DPoP"])["jwk"])

    assert signer(revoke) == old
    assert signer(login) == tmp_credentials.thumbprint != old
    assert sent.index(revoke) < sent.index(login)


def test_a_rotation_the_server_cannot_hear_still_rotates(
        logged_in, fake_v1, tmp_credentials, client_credentials, caplog):
    old = tmp_credentials.thumbprint
    fake_v1.route(responses.GET, "devices", "<html>502</html>", status=502,
                  content_type="text/html")
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    logged_in.rotate_key()

    assert tmp_credentials.thumbprint != old
    assert "releases the binding" in caplog.text
