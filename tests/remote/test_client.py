import json
import os
import stat
import sys

from pathlib import Path

import pytest
import responses

from unittest import mock

from siliconcompiler.remote import (
    Client, Credentials, RemoteError, ServerProblem)
from siliconcompiler.remote.client.errors import describe
from siliconcompiler.remote.client.transport import join_url, normalize_server

from conftest import V1_URL, problem


# Driven against the conformance rig: responses-based fixtures with no store,
# no scheduler and no port. It is the only place most of the contract can be
# reached from -- a working server cannot be made to emit use_dpop_nonce on
# demand, or report the device cap as exceeded, or hand back the HTML 502 a
# proxy in front of it would.


###########################
# Building a URL
###########################

def test_a_path_is_joined_not_urljoined():
    '''urljoin("https://host/v1", "jobs") is "https://host/jobs" -- the version
    prefix is silently dropped. That is fine until a server URL carries one,
    which is exactly what /v1 is.'''
    assert join_url("https://host/v1", "jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1", "/jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1/", "jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1") == "https://host/v1"


def test_the_scheme_comes_from_the_address_never_from_the_port():
    '''The client this replaces defaulted the port to 443 and then read the
    scheme off the port it had just defaulted, so a server on :8000 was reached
    over plaintext because of its port number -- which is every local
    deployment.'''
    assert normalize_server("http://localhost:8000") == "http://localhost:8000/v1"
    assert normalize_server("https://example.com") == "https://example.com/v1"

    # A bare address assumes the safe scheme rather than guessing from a port.
    assert normalize_server("example.com").startswith("https://")
    assert normalize_server("example.com", port=8000) == "https://example.com:8000/v1"


def test_a_server_url_may_already_carry_its_prefix():
    assert normalize_server("https://example.com/v1") == "https://example.com/v1"
    assert normalize_server("https://example.com/sc/v1") == "https://example.com/sc/v1"


###########################
# No server configured
###########################
#
# These four were written for an edge case and are now the normal one: there is
# no default server to fall back on, so an unconfigured client has nothing to
# talk to.

def test_a_client_without_a_server_still_builds():
    '''Constructing must not raise, or `sc-remote -configure` could not build
    one in order to fix it.'''
    client = Client(Credentials(Path("sc-home/credentials")))

    assert client.base_url is None


def test_a_client_without_a_server_reports_it_as_such(caplog):
    '''Never a server named None.'''
    import logging

    caplog.set_level(logging.INFO)
    Client(Credentials(Path("sc-home/credentials"))).print_configuration()

    assert "Server: not configured" in caplog.text


def test_a_client_without_a_server_names_the_way_to_fix_it():
    client = Client(Credentials(Path("sc-home/credentials")))

    with pytest.raises(RemoteError, match="No remote server address is configured"):
        client.capabilities()


def test_the_fix_is_a_command_the_user_can_run():
    client = Client(Credentials(Path("sc-home/credentials")))

    with pytest.raises(RemoteError, match="sc-remote -configure"):
        client.me()


###########################
# Credentials on disk
###########################

def test_the_credentials_file_is_private(tmp_credentials):
    '''A shipped security fix, and the floor rather than the starting point: a
    refresh token is a session, not one service's password.'''
    tmp_credentials.update(refresh_token="secret")

    assert _mode(tmp_credentials.path) == 0o600


def test_an_existing_wider_file_is_tightened(tmp_credentials):
    '''Re-running configure over a file somebody widened has to fix it.'''
    tmp_credentials.update(refresh_token="secret")
    os.chmod(tmp_credentials.path, 0o644)

    tmp_credentials.update(refresh_token="secret-again")

    assert _mode(tmp_credentials.path) == 0o600


def test_the_private_key_is_its_own_file_and_is_private(tmp_credentials):
    '''Beside the credentials rather than inside them, because
    scheduler/docker.py mounts ~/.sc into task containers and a separate file
    is something a narrower mount can leave out.'''
    tmp_credentials.key()

    assert tmp_credentials.key_path != tmp_credentials.path
    assert _mode(tmp_credentials.key_path) == 0o600
    assert "dpop_key" not in json.loads(tmp_credentials.path.read_text())


def test_the_key_is_generated_once_and_reused(tmp_credentials):
    '''A new key each run would be a new machine each run.'''
    first = tmp_credentials.thumbprint

    again = Credentials(tmp_credentials.path)

    assert again.thumbprint == first


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


if sys.platform == "win32":                                      # pragma: no cover
    test_the_credentials_file_is_private = pytest.mark.skip(
        reason="file modes are not enforced on windows")(
            test_the_credentials_file_is_private)
    test_an_existing_wider_file_is_tightened = pytest.mark.skip(
        reason="file modes are not enforced on windows")(
            test_an_existing_wider_file_is_tightened)
    test_the_private_key_is_its_own_file_and_is_private = pytest.mark.skip(
        reason="file modes are not enforced on windows")(
            test_the_private_key_is_its_own_file_and_is_private)


###########################
# Discovery
###########################

def test_capabilities_carry_no_credential(fake_v1, tmp_credentials, capabilities):
    '''The first call on every path, and what tells a client it reached a v1
    server at all.'''
    body = Client(tmp_credentials).capabilities()

    assert body == capabilities
    assert "Authorization" not in fake_v1.calls[0].request.headers


def test_every_request_carries_a_proof(fake_v1, tmp_credentials):
    Client(tmp_credentials).capabilities()

    assert fake_v1.calls[0].request.headers["DPoP"]


def test_health_is_one_word(fake_v1, tmp_credentials):
    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")

    assert Client(tmp_credentials).health() == {"status": "pass"}
    assert "Authorization" not in fake_v1.calls[-1].request.headers


def test_a_failing_health_arrives_as_a_503_and_is_still_an_answer(
        fake_v1, tmp_credentials):
    '''🔴 The endpoint serves its own worst value with a status a client
    would otherwise raise on. Reading it as `fail` is reading the endpoint
    correctly, not swallowing an error.'''
    fake_v1.route(responses.GET, "healthz", {"status": "fail"}, status=503,
                  content_type="application/health+json")

    assert Client(tmp_credentials).health() == {"status": "fail"}


def test_a_proxy_answering_for_a_dead_server_means_the_same_thing(
        fake_v1, tmp_credentials):
    '''Nothing that answers 503 on this path is serving, whatever it sends.'''
    fake_v1.route(responses.GET, "healthz", "<html>502 Bad Gateway</html>",
                  status=503, content_type="text/html")

    assert Client(tmp_credentials).health() == {"status": "fail"}


def test_the_deployment_report_is_what_the_server_says_it_is(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''🔴 Both halves unauthenticated, which is what makes this printable
    before enrolment and for a server that is down -- the two states somebody
    runs a bare `sc-remote` in.'''
    import logging

    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).print_deployment()

    assert "Health: pass" in caplog.text
    assert "API: v1" in caplog.text
    assert "Identity assurance: self_asserted" in caplog.text
    assert "siliconcompiler: 0.38.9" in caplog.text
    assert "client_credentials" in caplog.text
    assert "logs.stream" in caplog.text

    # Base units, rendered. The wire is bytes and seconds; a person reads
    # neither at this size.
    assert "max_upload_bytes: 1.0 GiB" in caplog.text
    assert "max_download_bytes: 100 MiB" in caplog.text
    assert "max_job_nodes: 1000" in caplog.text

    for call in fake_v1.calls:
        assert "Authorization" not in call.request.headers


def test_an_unlimited_limit_reads_as_unlimited_and_not_as_none(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''null is the wire's word for unlimited everywhere, and it is not zero.'''
    import logging

    capabilities["limits"]["max_download_bytes"] = None
    fake_v1.replace(responses.GET, "", capabilities)
    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).print_deployment()

    assert "max_download_bytes: unlimited" in caplog.text


def test_a_notice_is_a_warning_because_somebody_has_to_read_it(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''Scheduled downtime lives on `GET /v1` rather than the liveness probe:
    an announcement is read once by a person, at the start of a session, which
    is exactly when this runs.'''
    import logging

    capabilities["notices"] = [{"level": "warning", "message": "maintenance on Sunday",
                                "starts_at": "2026-09-27T02:00:00Z",
                                "ends_at": "2026-09-27T06:00:00Z"}]
    fake_v1.replace(responses.GET, "", capabilities)
    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).print_deployment()

    assert ("Notice: maintenance on Sunday (2026-09-27T02:00:00Z to "
            "2026-09-27T06:00:00Z)") in caplog.text
    assert any(record.levelname == "WARNING" and "maintenance" in record.message
               for record in caplog.records)


def notice(level, message, **times):
    return {"level": level, "message": message, "starts_at": None, "ends_at": None,
            **times}


def test_each_notice_is_shown_once_per_session_and_at_its_own_level(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''`level` picks how loudly and nothing branches on the text; a level
    this client does not know is shown as a warning, the cautious default.'''
    import logging

    capabilities["notices"] = [notice("info", "new tools image"),
                               notice("severe", "a level from a later server"),
                               notice("warning", "down Saturday",
                                      ends_at="2026-10-03T06:00:00Z")]
    fake_v1.replace(responses.GET, "", capabilities)
    caplog.set_level(logging.INFO)

    client = Client(tmp_credentials)
    client.capabilities()
    client.capabilities()

    shown = [(record.levelname, record.message) for record in caplog.records
             if record.message.startswith("Notice:")]
    assert shown == [("INFO", "Notice: new tools image"),
                     ("WARNING", "Notice: a level from a later server"),
                     ("WARNING", "Notice: down Saturday (until 2026-10-03T06:00:00Z)")]


def test_the_check_command_shows_every_notice_every_time(
        fake_v1, tmp_credentials, capabilities, caplog):
    import logging

    capabilities["notices"] = [notice("info", "new tools image")]
    fake_v1.replace(responses.GET, "", capabilities)
    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")
    caplog.set_level(logging.INFO)

    client = Client(tmp_credentials)
    client.capabilities()
    client.print_deployment()
    client.print_deployment()

    assert caplog.text.count("Notice: new tools image") == 3


def test_a_deprecation_warns_once_per_session_with_its_sunset(
        fake_v1, tmp_credentials, capabilities, caplog):
    import logging

    headers = {"Deprecation": "@1790000000", "Sunset": "Sat, 01 May 2027 00:00:00 GMT"}
    fake_v1.replace(responses.GET, "", capabilities, headers=headers)
    caplog.set_level(logging.INFO)

    client = Client(tmp_credentials)
    client.capabilities()
    client.capabilities()

    warned = [record for record in caplog.records if "deprecated" in record.message]
    assert len(warned) == 1
    assert warned[0].levelname == "WARNING"
    assert "Sat, 01 May 2027 00:00:00 GMT" in warned[0].message


###########################
# Upcoming terms
###########################

def terms_entry(accepted_at=None, decision_url="https://portal.test/terms/tos"):
    entry = {"id": "tos", "title": "Terms of Service", "scope": {"applies_to": "service"},
             "version": "2026-09-01", "accepted_at": "2026-09-02T00:00:00Z",
             "declined_at": None, "document_url": "https://portal.test/tos",
             "upcoming": {"version": "2026-11-01", "effective_at": "2026-11-01T00:00:00Z",
                          "accepted_at": accepted_at}}
    if decision_url:
        entry["decision_url"] = decision_url
    return entry


def me_body(*terms):
    return {"id": "u1", "issuer": "local", "projects": [], "can_submit": True,
            "limits": {}, "usage": {"jobs_active": 0}, "terms": list(terms)}


def test_an_upcoming_version_is_named_once_per_session_and_never_accepted(
        logged_in, fake_v1, caplog, monkeypatch):
    '''Before it takes effect, so the change need not first reach the person
    as a refused submit. 🔴 The client never accepts: nothing is sent.'''
    import logging

    from siliconcompiler.remote import client as client_module

    monkeypatch.setattr(client_module, "_ask",
                        lambda question: pytest.fail("asked without a terminal"))
    fake_v1.route(responses.GET, "me", me_body(terms_entry()))
    caplog.set_level(logging.INFO)

    logged_in.me()
    logged_in.me()

    named = [record.message for record in caplog.records if "2026-11-01" in record.message]
    assert len(named) == 1
    assert "Terms of Service" in named[0]
    assert "2026-11-01T00:00:00Z" in named[0]
    assert "accepted early, at https://portal.test/terms/tos" in caplog.text
    assert not [c for c in fake_v1.calls if c.request.method != "GET"
                and "/auth/" not in c.request.url]


def test_an_accepted_upcoming_version_is_not_mentioned(logged_in, fake_v1, caplog):
    import logging

    fake_v1.route(responses.GET, "me",
                  me_body(terms_entry(accepted_at="2026-10-01T00:00:00Z", decision_url=None)))
    caplog.set_level(logging.INFO)

    logged_in.me()

    assert "2026-11-01" not in caplog.text


def test_on_a_terminal_the_page_is_offered_and_opened_only_when_asked(
        logged_in, fake_v1, monkeypatch):
    from siliconcompiler.remote import client as client_module

    for stream in ("stdin", "stdout"):
        monkeypatch.setattr(f"sys.{stream}.isatty", lambda: True)
    monkeypatch.delenv("CI", raising=False)
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    answers = iter(["n", "y"])
    monkeypatch.setattr(client_module, "_ask", lambda question: next(answers))
    fake_v1.route(responses.GET, "me", me_body(terms_entry()))

    logged_in.me()
    assert opened == []

    # Every time in the check command.
    logged_in.remind_terms(me_body(terms_entry()), always=True)
    assert opened == ["https://portal.test/terms/tos"]


def test_a_ci_run_only_reports_an_upcoming_version(logged_in, fake_v1, monkeypatch,
                                                   caplog):
    import logging

    from siliconcompiler.remote import client as client_module

    for stream in ("stdin", "stdout"):
        monkeypatch.setattr(f"sys.{stream}.isatty", lambda: True)
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(client_module, "_ask",
                        lambda question: pytest.fail("offered to open it in CI"))
    fake_v1.route(responses.GET, "me", me_body(terms_entry()))
    caplog.set_level(logging.INFO)

    logged_in.me()

    assert "2026-11-01" in caplog.text


###########################
# Login
###########################

def test_login_needs_no_human(fake_v1, tmp_credentials, client_credentials):
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    body = Client(tmp_credentials).login()

    assert body["access_token"] == "access-token-one"
    assert tmp_credentials.refresh_token == "refresh-token-one"
    # 🔴 The access token is never written down: it lives fifteen minutes and
    # this file lives for weeks.
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())


def test_login_asserts_a_derived_subject(fake_v1, tmp_credentials, client_credentials):
    '''client_id=local:<derivation>, which RFC 6749 already registers -- so a
    username is not invented.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    Client(tmp_credentials).login()

    sent = _form(fake_v1.calls[-1].request.body)
    assert sent["grant_type"] == "client_credentials"
    assert sent["client_id"].startswith("local:")
    assert sent["machine_id_source"] in (
        "linux_machine_id", "macos_platform_uuid", "windows_machine_guid")


def test_no_fingerprint_no_access(fake_v1, tmp_credentials, client_credentials):
    '''🔴 With no machine id every such host would derive one subject -- one
    principal for all of them -- so the client refuses before it asks.'''
    from siliconcompiler.remote.client import identity

    fake_v1.route(responses.POST, "auth/token", client_credentials)

    with mock.patch.object(identity, "machine_fingerprint", return_value=(None, "none")):
        with pytest.raises(RemoteError, match="no id to sign in with"):
            Client(tmp_credentials).login()

    assert not [call for call in fake_v1.calls if "auth/token" in call.request.url]


def test_the_derivation_includes_the_uid(tmp_credentials):
    '''A machine-only key would collapse every user on a login node into one
    identity, and B could cancel A's jobs.'''
    from siliconcompiler.remote.client.identity import local_subject

    subject, _, _ = local_subject()
    uid = str(os.getuid()) if hasattr(os, "getuid") else None

    if uid is not None:
        assert subject.endswith(f":{uid}")


def test_the_machine_label_is_not_the_subject(tmp_credentials):
    '''Two different columns: users.subject is the identity key and is unique,
    devices.machine_id_hash is a label and deliberately is not.'''
    from siliconcompiler.remote.client.identity import local_subject

    subject, label, _ = local_subject()

    assert label is None or label != subject


def test_the_next_command_refreshes_rather_than_enrolling_again(
        fake_v1, tmp_credentials, client_credentials):
    '''🔴 The property that matters is WHICH grant the second process uses.

    The access token is not written down, so a later command always goes to the
    token endpoint -- and it must go with `refresh_token`. `client_credentials`
    mints a NEW token family every time it is called and a family lives twelve
    days whether or not anything uses it, so enrolling per command would leave
    one live session behind per invocation.
    '''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).login()

    # A second client, as a second process would be.
    Client(Credentials(tmp_credentials.path)).me()

    grants = [_form(c.request.body)["grant_type"]
              for c in fake_v1.calls if c.request.method == "POST"]
    assert grants == ["client_credentials", "refresh_token"]


def test_a_first_command_with_nothing_stored_enrolls(fake_v1, tmp_credentials,
                                                     client_credentials):
    '''And the fallback still exists: no refresh token means no session to
    renew, so the grant is the one that creates one.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()

    grants = [_form(c.request.body)["grant_type"]
              for c in fake_v1.calls if c.request.method == "POST"]
    assert grants == ["client_credentials"]


def test_a_dead_refresh_token_falls_back_to_enrolling(fake_v1, tmp_credentials,
                                                      client_credentials):
    '''A session that ended is not a session to renew, and this machine's key
    is still enrolled -- so the answer is a new session, not a failure.'''
    tmp_credentials.update_session(refresh_token="long-dead")

    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_grant", "reason": "revoked"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert Client(tmp_credentials).me()["id"] == "u1"

    grants = [_form(c.request.body)["grant_type"]
              for c in fake_v1.calls if c.request.method == "POST"]
    assert grants == ["refresh_token", "client_credentials"]


def test_an_access_token_left_by_an_older_client_is_dropped(tmp_credentials):
    '''Popped on read rather than only on write, so a file written by a client
    that stored one can never have it read back.'''
    values = json.loads(tmp_credentials.path.read_text())
    values["access_token"] = "left-behind"
    tmp_credentials.path.write_text(json.dumps(values))

    reopened = Credentials(tmp_credentials.path)
    assert not hasattr(reopened, "access_token")

    reopened.update(refresh_token="fresh")
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())


###########################
# The three things a 401 means
###########################

def test_an_expired_token_is_refreshed_silently(fake_v1, tmp_credentials,
                                                client_credentials):
    '''The session is alive and the access token is not. The user sees
    nothing.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", problem("invalid-token", 401), status=401,
                  content_type="application/problem+json",
                  headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "access_token": "access-token-two"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert client.me()["id"] == "u1"
    # The rotated refresh token is persisted; the new access token is not.
    assert tmp_credentials.refresh_token == "refresh-token-one"
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())


def test_a_nonce_challenge_is_retried_not_refreshed(fake_v1, tmp_credentials,
                                                    client_credentials):
    '''A client that only refreshes loops here forever, which is why all three
    branches have to exist at once.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", problem("invalid-dpop-proof", 401), status=401,
                  content_type="application/problem+json",
                  headers={"WWW-Authenticate": 'DPoP error="use_dpop_nonce"',
                           "DPoP-Nonce": "nonce-from-the-server"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert client.me()["id"] == "u1"

    # The retry carried the nonce, and no second login happened.
    retried = fake_v1.calls[-1].request
    assert "nonce-from-the-server" in _proof_claims(retried.headers["DPoP"])["nonce"]
    assert len([c for c in fake_v1.calls if c.request.method == "POST"]) == 1


def test_a_dead_session_is_logged_into_again_never_refreshed(fake_v1, tmp_credentials,
                                                             client_credentials):
    '''Refreshing a revoked session loops; retrying it as it is loops. The
    answer is a new login -- and never a refresh, because the refresh token is
    the session that ended.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me",
                  problem("session-ended", 401, reason="revoked"), status=401,
                  content_type="application/problem+json")
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert client.me()["id"] == "u1"

    grants = [_form(c.request.body)["grant_type"]
              for c in fake_v1.calls if c.request.method == "POST"]
    assert grants == ["client_credentials", "client_credentials"]


def test_a_reused_refresh_token_says_to_rotate_the_key(fake_v1, tmp_credentials,
                                                       client_credentials, caplog):
    '''`reused` means the credentials were used somewhere else: the person is
    told to replace this machine's key, and on a `client_credentials` server
    that an operator must release the binding.'''
    tmp_credentials.update_session(refresh_token="stolen-and-spent")
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_grant", "reason": "reused"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    with caplog.at_level("WARNING"):
        Client(tmp_credentials).me()

    assert "sc-remote -rotate_key" in caplog.text
    assert "used elsewhere" in caplog.text


def test_an_invalid_proof_fails_rather_than_refreshing(fake_v1, tmp_credentials,
                                                       client_credentials):
    '''A bad proof is not a stale token, so there is nothing a refresh would
    fix.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", problem("invalid-dpop-proof", 401),
                  status=401, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        client.me()

    assert raised.value.slug == "invalid-dpop-proof"


# Clear of each unit's boundary: `Date` has one-second resolution.
@pytest.mark.parametrize("offset,said", [(330, "5 minutes behind"), (-7500, "2 hours ahead"),
                                         (20, None)])
def test_a_refused_proof_says_when_the_clock_is_off(fake_v1, tmp_credentials,
                                                    client_credentials, offset, said):
    '''🔴 Surface D167: a clock further than a minute from the server's is
    refused every time, and "did not accept this machine's key" sends a person
    looking at the key. The server's `Date` says how far out it is.'''
    import email.utils
    import time as clock

    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", problem("invalid-dpop-proof", 401), status=401,
                  content_type="application/problem+json",
                  headers={"Date": email.utils.formatdate(clock.time() + offset, usegmt=True)})

    with pytest.raises(ServerProblem) as raised:
        client.me()

    if said:
        assert said in str(raised.value) and "clock" in str(raised.value)
    else:
        assert "clock is" not in str(raised.value)


###########################
# Identity continuity
###########################

def test_a_changed_identity_is_reported_rather_than_read_as_lost_jobs(
        fake_v1, tmp_credentials, client_credentials, caplog):
    '''Five things replace the principal without anyone doing anything wrong: a
    reimage, a container, a CI image, a changed uid, a client release that
    changes the salt. Without the persisted id, a user cannot tell "my jobs were
    deleted" from "I am a different person now".'''
    import logging

    caplog.set_level(logging.WARNING)
    tmp_credentials.update(user_id="the-old-me")

    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "the-new-me", "issuer": "local"})

    Client(tmp_credentials).me()

    assert "different user" in caplog.text
    assert tmp_credentials.user_id == "the-new-me"


###########################
# Rendering a refusal
###########################

def test_a_refusal_is_three_lines_without_opening_a_url():
    '''The type pages are static and identical across deployments, so the
    client holds the only copy of the specific failure -- and most users never
    open the link.'''
    rendered = describe(problem("limit-exceeded", 429, limit="concurrent_jobs",
                                detail="four already running",
                                trace_id="a" * 32))

    assert "four already running" in rendered
    assert "limit: concurrent_jobs" in rendered
    assert "refills" in rendered
    assert "trace " + "a" * 32 in rendered


def test_the_discriminator_is_rendered_not_just_the_slug():
    '''A slug names a kind of failure; the member names the instance.'''
    assert "feature: device_grant" in describe(
        problem("feature-unsupported", 501, feature="device_grant"))
    assert "reason: expanded_bytes" in describe(
        problem("archive-rejected", 422, reason="expanded_bytes"))


def test_a_proxy_html_error_renders_rather_than_throwing(fake_v1, tmp_credentials,
                                                         client_credentials):
    '''problem+json is promised only for what a handler produced, so
    resp.json()["type"] throws on exactly the errors production serves most.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me",
                  "<html><head><title>502 Bad Gateway</title></head>"
                  "<body><h1>502 Bad Gateway</h1></body></html>",
                  status=502, content_type="text/html")

    with pytest.raises(ServerProblem) as raised:
        client.me()

    assert raised.value.status == 502
    assert raised.value.slug is None            # nothing named a condition
    assert "502" in str(raised.value)
    assert "<html>" not in str(raised.value)    # not the whole page


def test_an_empty_error_body_still_renders(fake_v1, tmp_credentials,
                                           client_credentials):
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", "", status=503, content_type="text/plain")

    with pytest.raises(ServerProblem) as raised:
        client.me()

    assert raised.value.status == 503
    assert str(raised.value)


###########################
# Refusals only this rig can produce
###########################

@pytest.mark.parametrize("slug,status,members", [
    ("limit-exceeded", 429, {"limit": "concurrent_jobs"}),
    ("feature-unsupported", 501, {"feature": "projects"}),
    ("entitlement-denied", 403, {"resource_kind": "pdk", "resource": "gf12"}),
    ("terms-not-accepted", 403, {"blocked_by": {"tos": {}}}),
    ("rate-limited", 429, {}),
    ("insecure-transport", 426, {}),
    ("not-ready", 409, {"artifact_kind": "logs"}),
    ("invalid-cursor", 400, {}),
])
def test_every_refusal_branches_on_its_type(fake_v1, tmp_credentials,
                                            client_credentials, slug, status,
                                            members):
    '''Most of these cannot be provoked from a working server at all, which is
    the whole argument for this rig: branch coverage becomes a function of the
    frozen registry rather than of what a real server happens to say.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "me", problem(slug, status, **members),
                  status=status, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        client.me()

    assert raised.value.slug == slug
    for name, value in members.items():
        assert raised.value.member(name) == value


def test_an_unknown_type_is_acted_on_by_its_status(fake_v1, logged_in):
    '''A type from a later registry is not a type this client knows, and
    the status still says what to do: a 4xx is not worth repeating.'''
    fake_v1.route(responses.GET, "me", problem("a-type-from-later", 422),
                  status=422, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.slug == "a-type-from-later"
    assert "retrying it unchanged will not help" in str(raised.value)


def test_an_unknown_reason_is_acted_on_by_its_type():
    text = describe(problem("archive-rejected", 422, reason="a-reason-from-later"))

    assert "Fix what the reason names, in a new job." in text


def test_an_untyped_5xx_says_to_try_later():
    assert "try again later" in describe({"title": "Bad Gateway"}, 502)


###########################
# Devices
###########################

def test_devices_follow_the_next_link(fake_v1, logged_in):
    fake_v1.route(responses.GET, "devices", {"items": [{"id": "d1"}]},
                  headers={"Link": f'<{V1_URL}/devices?cursor=c2>; rel="next"'})
    fake_v1.route(responses.GET, "devices", {"items": [{"id": "d2"}]})

    assert [device["id"] for device in logged_in.devices()] == ["d1", "d2"]
    assert fake_v1.calls[-1].request.url.endswith("cursor=c2")


def test_devices_are_listed_and_revoked(fake_v1, tmp_credentials,
                                        client_credentials):
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.GET, "devices",
                  {"items": [{"id": "d1", "name": "laptop", "current": True}]})
    assert client.devices()[0]["id"] == "d1"

    fake_v1.route(responses.DELETE, "devices/d1", "", status=204)
    client.revoke_device("d1")

    assert fake_v1.calls[-1].request.method == "DELETE"


def test_logout_ends_the_session_and_forgets_it(fake_v1, tmp_credentials,
                                                client_credentials):
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.POST, "auth/revoke", "", status=204)
    client.logout()

    assert tmp_credentials.refresh_token is None


def test_logout_of_an_already_dead_session_still_forgets_it(
        fake_v1, tmp_credentials, client_credentials):
    '''The remaining job is local, and failing here would leave a user unable to
    log out of a session that is already gone.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    client = Client(tmp_credentials)
    client.login()

    fake_v1.route(responses.POST, "auth/revoke",
                  problem("session-ended", 401, reason="revoked"), status=401,
                  content_type="application/problem+json")
    client.logout()

    assert tmp_credentials.refresh_token is None


def _form(body):
    from urllib.parse import parse_qs

    if isinstance(body, bytes):
        body = body.decode()
    return {k: v[0] for k, v in parse_qs(body).items()}


def _proof_claims(proof):
    import jwt

    return jwt.decode(proof, options={"verify_signature": False})


def test_reconfiguring_forgets_which_principal_the_old_server_used(
        fake_v1, tmp_credentials, client_credentials, capabilities):
    '''Pointing at a different server is not identity drift.

    `user_id` is per server, so keeping one across a change of address would
    have the first `me()` announce that this machine became somebody else --
    on the one occasion when a different principal is exactly what was asked
    for.
    '''
    tmp_credentials.update(user_id="who-the-old-server-called-me")

    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-new", "issuer": "local"})

    client = Client(tmp_credentials)
    client.configure_server(server=V1_URL.rsplit("/v1", 1)[0],
                            clobber=True, prompt=False)

    assert tmp_credentials.user_id == "u-new"


def test_the_derivation_salt_is_pinned():
    '''🔴 Editing this constant is a silent, uncoordinated identity migration.

    The salt is compile-time and ships in the source. It provides domain
    separation, NOT secrecy -- anybody with the source computes the same
    digest, which is fine, because its whole job is to keep this project's
    hash of a machine id different from every other program's hash of the same
    machine id.

    What it must never do is change. Every unauthenticated deployment derives
    its subjects from it, so a new value makes every existing user a stranger
    on every server at once: their jobs are still there and are no longer
    theirs. There is no migration path, because the server cannot know the old
    subject and the new one are the same person.

    A comment asking for that is not a gate. This is.
    '''
    from siliconcompiler.remote.client import identity

    assert identity._SALT == b"siliconcompiler.remote.v1"

    # And the shape it produces, so a change to the derivation ITSELF is caught
    # too -- reordering the inputs or dropping a separator is the same break
    # with none of the visibility.
    with mock.patch.object(identity, "machine_fingerprint",
                           return_value=("a-machine-id", "linux_machine_id")), \
         mock.patch.object(identity, "_uid", return_value="1000"):
        subject, label, source = identity.local_subject()

    assert subject == "ef75e01d65b55facdf7413b2840745d7:1000"
    assert label == "7eb20bb0b9607154b02dac185bb497d7"
    assert source == "linux_machine_id"


###########################
# 🔴 A refusal must never become a flood
###########################

def test_a_stale_refresh_token_does_not_recurse(fake_v1, tmp_credentials,
                                                client_credentials):
    '''🔴 A 401 from the TOKEN endpoint is not an expired access token.

    Treating it as one made the client refresh in answer to a failed refresh,
    and the loop was not bounded by the retry counter: every hop went through
    login(), which starts a fresh request with the counter back at zero. It
    ended in a RecursionError after a couple of hundred REAL round trips, so
    the client flooded the server on its way to crashing.
    '''
    tmp_credentials.update_session(refresh_token="long-since-revoked")

    fake_v1.route(responses.POST, "auth/token", {"error": "invalid_grant"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert Client(tmp_credentials).me()["id"] == "u1"

    grants = [_form(c.request.body)["grant_type"]
              for c in fake_v1.calls if c.request.method == "POST"]
    # Exactly two: the refresh that was refused, then the enrolment that
    # replaced it. Not a third, and certainly not two hundred.
    assert grants == ["refresh_token", "client_credentials"]


def test_a_stale_refresh_token_is_replaced_on_disk(fake_v1, tmp_credentials,
                                                   client_credentials):
    '''Self-healing, so the next command costs one request rather than two.'''
    tmp_credentials.update_session(refresh_token="long-since-revoked")

    fake_v1.route(responses.POST, "auth/token", {"error": "invalid_grant"}, status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()

    assert tmp_credentials.refresh_token == "refresh-token-one"


def test_an_unauthenticated_request_never_refreshes(fake_v1, tmp_credentials):
    '''There is no access token on one, so there is nothing a refresh could
    repair.'''
    tmp_credentials.update(refresh_token="whatever")

    fake_v1.route(responses.POST, "auth/token",
                  problem("invalid-token", 401), status=401,
                  content_type="application/problem+json")

    client = Client(tmp_credentials)
    with pytest.raises(ServerProblem):
        client.transport.login({"grant_type": "refresh_token",
                                "refresh_token": "whatever"})

    posts = [c for c in fake_v1.calls if c.request.method == "POST"]
    assert len(posts) == 1


def test_a_refresh_cannot_start_inside_a_refresh(fake_v1, tmp_credentials):
    '''Belt and braces behind the check above. A refresh that provokes a
    refresh is the one failure here that costs the SERVER rather than this
    process, so it is impossible by construction rather than by one condition
    being right.'''
    client = Client(tmp_credentials)
    client.transport.set_tokens(None, "a-token")

    client.transport._refreshing = True
    assert client.transport.refresh() is False
    assert not fake_v1.calls[1:]        # nothing beyond discovery


def test_configure_says_what_the_server_runs(fake_v1, tmp_credentials,
                                             client_credentials, caplog):
    '''🔴 The check is the client's and the decision is the server's.

    A client that skips it is not broken -- it gets a `version-skew` a moment
    later -- and a server that trusted it would be. What saying it here buys is
    that the mismatch is visible while somebody is watching, rather than at the
    first submit of the first job.
    '''
    import logging

    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-1", "issuer": "local"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).configure_server(
        server=V1_URL.rsplit("/v1", 1)[0], clobber=True, prompt=False)

    assert "This server runs siliconcompiler 0.38.9" in caplog.text


def test_configure_says_so_when_this_machine_is_not_on_the_list(
        fake_v1, capabilities, tmp_credentials, client_credentials, caplog):
    '''Before a job exists, which is the cheapest possible refusal.'''
    import logging

    capabilities["software"] = {"python": {"siliconcompiler": ["9.9.9"]},
                                "tools": {}}
    fake_v1.replace(responses.GET, "", capabilities)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-1", "issuer": "local"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).configure_server(
        server=V1_URL.rsplit("/v1", 1)[0], clobber=True, prompt=False)

    assert "which is not one of them" in caplog.text
    assert "before anything is uploaded" in caplog.text


def test_a_server_that_names_no_software_is_not_second_guessed(
        fake_v1, capabilities, tmp_credentials, client_credentials, caplog):
    '''REQUIRED on the wire, so its absence is an older or a broken server
    rather than a deployment with an opinion.'''
    import logging

    capabilities["software"] = {"python": {}, "tools": {}}
    fake_v1.replace(responses.GET, "", capabilities)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-1", "issuer": "local"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).configure_server(
        server=V1_URL.rsplit("/v1", 1)[0], clobber=True, prompt=False)

    assert "This server runs" not in caplog.text
