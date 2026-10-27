import json
import logging
import os
import re

from pathlib import Path

import pytest
import responses

from unittest import mock

from siliconcompiler.remote import (
    Client, Credentials, RemoteError, ServerProblem)
from siliconcompiler.remote.client import cli
from siliconcompiler.remote.client.errors import REGISTERED, TYPE_BASE
from siliconcompiler.remote.client.transport import join_url, normalize_server

from conftest import V1_URL, asked_for_pages, claims, form, grants, problem


def _healthy(fake_v1):
    fake_v1.route(responses.GET, "healthz", {"status": "pass"},
                  content_type="application/health+json")


def test_a_path_is_joined_not_urljoined():
    '''urljoin("https://host/v1", "jobs") drops the version prefix.'''
    assert join_url("https://host/v1", "jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1", "/jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1/", "jobs") == "https://host/v1/jobs"
    assert join_url("https://host/v1") == "https://host/v1"


@pytest.mark.parametrize("given,port,expected", [
    ("http://localhost:8000", None, "http://localhost:8000/v1"),
    ("https://example.com", None, "https://example.com/v1"),
    ("example.com", None, "https://example.com/v1"),
    ("example.com", 8000, "https://example.com:8000/v1"),
    ("https://example.com/v1", None, "https://example.com/v1"),
    ("https://example.com/sc/v1", None, "https://example.com/sc/v1"),
    ("https://[::1]:8000", None, "https://[::1]:8000/v1"),
    ("https://[::1]", 8000, "https://[::1]:8000/v1"),
    ("http://[fd00::5]:8080/sc", None, "http://[fd00::5]:8080/sc"),
])
def test_a_server_address_is_normalized(given, port, expected):
    '''The scheme comes from the address, never the port (the old client
    reached :8000 over plaintext); a bare address is https; IPv6 brackets and
    an existing prefix are kept.'''
    assert normalize_server(given, port) == expected


def test_a_username_and_password_in_an_address_are_dropped():
    '''The key is the credential: nothing of the userinfo is kept.'''
    assert normalize_server("https://me:secret@example.com") == "https://example.com/v1"


def test_a_client_without_a_server_builds_and_says_so(caplog):
    '''Constructing must not raise, or `sc-config remote configure` could not fix it.'''
    caplog.set_level(logging.INFO)
    client = Client(Credentials(Path("sc-home/auth/remote.json")))
    cli.print_configuration(client)

    assert client.base_url is None
    assert "Server: not configured" in caplog.text
    with pytest.raises(RemoteError, match="No remote server address is configured"):
        client.capabilities()
    with pytest.raises(RemoteError, match="sc-config remote configure"):
        client.me()


def test_capabilities_carry_no_credential_and_a_proof(fake_v1, tmp_credentials, capabilities):
    body = Client(tmp_credentials).capabilities()

    assert body == capabilities
    assert "Authorization" not in fake_v1.calls[0].request.headers
    assert fake_v1.calls[0].request.headers["DPoP"]


def test_the_rigs_capabilities_carry_every_required_member(capabilities):
    '''The conformance rig's copy of a real `GET /v1`.'''
    assert {"api_version", "software", "grant_types_supported", "limits", "features",
            "identity_assurance", "notices"} <= set(capabilities)
    assert capabilities["api_version"] == "v1"
    # A closed set of buckets, and `siliconcompiler` REQUIRED in `python`.
    assert set(capabilities["software"]) == {"python", "tools", "interpreter"}
    assert "siliconcompiler" in capabilities["software"]["python"]
    # This profile serves no device grant, so it must not advertise one.
    assert "urn:ietf:params:oauth:grant-type:device_code" \
        not in capabilities["grant_types_supported"]
    assert set(capabilities["limits"]) == {
        "max_job_nodes", "max_upload_bytes", "artifact_retention_seconds",
        "pending_uploads", "concurrent_jobs", "concurrent_log_streams",
        "max_archive_members", "max_archive_expanded_bytes",
        "max_download_bytes", "abandon_after_seconds"}
    # OPTIONAL: absent, not empty.
    assert "terms_url" not in capabilities


@pytest.mark.parametrize("body,status,content_type,expected", [
    ({"status": "pass"}, 200, "application/health+json", "pass"),
    ({"status": "fail"}, 503, "application/health+json", "fail"),
    ("<html>502 Bad Gateway</html>", 503, "text/html", "fail"),
], ids=["pass", "fail", "proxy"])
def test_health_is_one_word_and_a_503_is_an_answer(fake_v1, tmp_credentials, body, status,
                                                   content_type, expected):
    '''The endpoint serves `fail` as a 503, and nothing answering 503 here
    is serving, whatever it sends.'''
    fake_v1.route(responses.GET, "healthz", body, status=status, content_type=content_type)

    assert cli.health(Client(tmp_credentials)) == {"status": expected}
    assert "Authorization" not in fake_v1.calls[-1].request.headers


def test_the_deployment_report_is_what_the_server_says_it_is(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''Unauthenticated, so it prints before enrolment and for a server
    that is down. Limits in readable units; null is unlimited, not zero.'''
    capabilities["limits"]["concurrent_jobs"] = None
    fake_v1.replace(responses.GET, "", capabilities)
    _healthy(fake_v1)

    caplog.set_level(logging.INFO)
    cli.print_deployment(Client(tmp_credentials))

    for said in ("Health: pass", "API: v1", "Identity assurance: self_asserted",
                 "siliconcompiler: 0.38.9", "client_credentials", "logs.stream",
                 "max_upload_bytes: 1.0 GiB", "max_download_bytes: 100 MiB",
                 "max_job_nodes: 1000", "concurrent_jobs: unlimited"):
        assert said in caplog.text
    for call in fake_v1.calls:
        assert "Authorization" not in call.request.headers


def notice(level, message, **times):
    return {"level": level, "message": message, "starts_at": None, "ends_at": None,
            **times}


def test_each_notice_is_shown_once_per_session_and_at_its_own_level(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''A level this client does not know is a warning, the cautious default.'''
    capabilities["notices"] = [notice("info", "new tools image"),
                               notice("severe", "a level from a later server"),
                               notice("warning", "maintenance on Sunday",
                                      starts_at="2026-09-27T02:00:00Z",
                                      ends_at="2026-09-27T06:00:00Z"),
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
                     ("WARNING", "Notice: maintenance on Sunday (2026-09-27T02:00:00Z to "
                                 "2026-09-27T06:00:00Z)"),
                     ("WARNING", "Notice: down Saturday (until 2026-10-03T06:00:00Z)")]


def test_the_check_command_shows_every_notice_every_time(
        fake_v1, tmp_credentials, capabilities, caplog):
    capabilities["notices"] = [notice("info", "new tools image")]
    fake_v1.replace(responses.GET, "", capabilities)
    _healthy(fake_v1)
    caplog.set_level(logging.INFO)

    client = Client(tmp_credentials)
    client.capabilities()
    cli.print_deployment(client)
    cli.print_deployment(client)

    assert caplog.text.count("Notice: new tools image") == 3


def test_a_deprecation_warns_once_per_session_with_its_sunset(
        fake_v1, tmp_credentials, capabilities, caplog):
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


def terms_entry(accepted_at=None, can_decide=True):
    '''A `terms` entry as the v1 API has it: `can_decide`, and no URL.'''
    return {"id": "tos", "title": "Terms of Service", "scope": {"applies_to": "service"},
            "version": "2026-09-01", "accepted_at": "2026-09-02T00:00:00Z",
            "declined_at": None, "can_decide": can_decide,
            "upcoming": {"version": "2026-11-01", "effective_at": "2026-11-01T00:00:00Z",
                         "accepted_at": accepted_at}}


def me_body(*terms):
    return {"id": "u1", "issuer": "local", "projects": [], "can_submit": True,
            "limits": {}, "usage": {"concurrent_jobs": 0}, "terms": list(terms)}


def _asked(monkeypatch, answer=None, tty=False, ci=False):
    from siliconcompiler.remote import client as client_module

    if tty:
        for stream in ("stdin", "stdout"):
            monkeypatch.setattr(f"sys.{stream}.isatty", lambda: True)
    if ci:
        monkeypatch.setenv("CI", "true")
    else:
        monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(client_module, "_ask",
                        answer or (lambda question: pytest.fail("asked")))


@pytest.mark.parametrize("tty,ci,entry,answers,named,early,pages,opened", [
    # Named once, with where it can be accepted; never accepted by the client.
    pytest.param(False, False, {}, None, 1, True, [], 0, id="named-once"),
    pytest.param(False, False, {"accepted_at": "2026-10-01T00:00:00Z"}, None, 0, False,
                 [], 0, id="accepted-is-not-mentioned"),
    pytest.param(True, False, {}, ["n", "y"], 2, True, [{"terms_id": "tos"}], 1,
                 id="offered-and-opened-on-a-yes"),
    pytest.param(True, False, {"can_decide": False}, None, 1, False, [], 0,
                 id="page-cannot-decide"),
    pytest.param(True, True, {}, None, 1, True, [], 0, id="ci"),
])
def test_an_upcoming_terms_version_is_named_and_a_page_offered_only_where_it_can_be(
        logged_in, fake_v1, monkeypatch, caplog, tty, ci, entry, answers, named, early,
        pages, opened):
    '''Named before it takes effect, once per session; a page is asked for and opened
    only on a terminal, where the client's question was answered yes.'''
    replies = iter(answers or ())
    _asked(monkeypatch, (lambda question: next(replies)) if answers else None, tty=tty, ci=ci)
    urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: urls.append(url) or True)
    fake_v1.route(responses.GET, "me", me_body(terms_entry(**entry)))
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://portal.test/enter?token=t1", "expires_at": None})
    caplog.set_level(logging.INFO)

    logged_in.me()
    logged_in.me()
    if answers:
        assert urls == [] and asked_for_pages(fake_v1) == []
        logged_in.terms_reminded.clear()
        logged_in.remind_terms(me_body(terms_entry(**entry)))

    said = [record.message for record in caplog.records if "2026-11-01" in record.message]
    assert len(said) == named
    if named:
        assert "Terms of Service" in said[0] and "2026-11-01T00:00:00Z" in said[0]
    assert ("accepted early, on its page in this server's portal" in caplog.text) is early
    assert asked_for_pages(fake_v1) == pages
    assert urls == ["https://portal.test/enter?token=t1"] * opened
    assert not [c for c in fake_v1.calls if c.request.method != "GET"
                and "/auth/" not in c.request.url]


EVIL = "\x1b]0;owned\x07"


def _blocked_account():
    body = me_body(
        terms_entry(),
        dict(terms_entry(), id="gf12-nda", title="gf12 NDA", accepted_at=None,
             declined_at="2026-06-20T14:30:00Z", upcoming=None),
        dict(terms_entry(can_decide=False), id="export", title="Export terms",
             accepted_at=None, upcoming=None),
        dict(terms_entry(), id="data", title="Data policy", accepted_at=None, upcoming=None))
    body.update(
        can_submit=False,
        blocked_type="https://siliconcompiler.com/server-errors/account-not-provisioned",
        limits={"max_job_nodes": 50, "concurrent_jobs": None},
        usage={"concurrent_jobs": 3,
               "compute_seconds": {"used": 60, "total": None, "limit": None,
                                   "window": "calendar_week", "resets_at": None}})
    return body


@pytest.mark.parametrize("body,said,unsaid,asked", [
    pytest.param(
        _blocked_account(),
        ["You cannot submit jobs here", "Ask an administrator to provision",
         "server-errors/account-not-provisioned",
         "Your limits:", "max_job_nodes: 50", "concurrent_jobs: unlimited",
         "Unfinished jobs (staging, queued, running or cancelling): 3",
         "Compute: 1m 00s in this calendar_week window",
         "Terms of Service, version 2026-09-01: accepted",
         "gf12 NDA, version 2026-09-01: declined",
         "Export terms, version 2026-09-01: undecided",
         "Data policy, version 2026-09-01: undecided"],
        [], 2, id="account"),
    pytest.param(
        {"id": "u1", "issuer": "local",
         "session": {"kind": "interactive", "scope": "jobs:read jobs:write",
                     "device_id": "dev-1", "access_expires_at": "2026-09-29T10:15:00.000Z",
                     "refresh_expires_at": "2026-10-06T10:00:00.000Z",
                     "session_expires_at": "2026-10-11T10:00:00.000Z"},
         "usage": {"concurrent_jobs": 2,
                   "compute_seconds": {"used": 3600, "total": 7200, "limit": None,
                                       "window": "calendar_month", "resets_at": "x"},
                   "storage_bytes": {"used": 2048, "total": None, "limit": None,
                                     "window": None, "resets_at": None}}},
        ["Session: interactive on device dev-1", "scope: jobs:read jobs:write",
         "refresh token until 2026-10-06T10:00:00.000Z",
         "ends at 2026-10-11T10:00:00.000Z", "Compute: 1h 00m this month, 2h 00m in all"],
        [], 0, id="interactive-session"),
    pytest.param(
        {"id": "u1", "issuer": "ci",
         "session": {"kind": "ci", "scope": "jobs:read", "device_id": None,
                     "access_expires_at": "a", "refresh_expires_at": None,
                     "session_expires_at": "s"},
         "usage": {"concurrent_jobs": 0}},
        ["Session: ci", "it cannot refresh"], ["on device"], 0, id="ci-session"),
    pytest.param(
        {"id": EVIL, "issuer": EVIL, "can_submit": False, "blocked_type": EVIL,
         "session": {"kind": EVIL, "scope": EVIL, "device_id": EVIL,
                     "access_expires_at": EVIL, "refresh_expires_at": EVIL,
                     "session_expires_at": EVIL},
         "limits": {EVIL: EVIL}, "usage": {"concurrent_jobs": EVIL},
         "terms": [{"id": "tos", "title": EVIL, "version": EVIL, "can_decide": False}]},
        [], [], 0, id="control-characters"),
])
def test_the_account_view_shows_the_session_limits_usage_and_every_terms_decision(
        logged_in, fake_v1, monkeypatch, caplog, body, said, unsaid, asked):
    '''What `GET /v1/me` says and nothing refreshed; the reminder offers each page once
    where it can still be decided; server text never carries a control character.'''
    questions = []
    _asked(monkeypatch, lambda question: questions.append(question) or "n", tty=True)
    fake_v1.route(responses.GET, "me", body)
    caplog.set_level(logging.INFO)

    cli.print_identity(logged_in, logged_in.me())

    for line in said:
        assert line in caplog.text, line
    assert not any(line in caplog.text for line in unsaid)
    assert "\x07" not in caplog.text and "\x1b]" not in caplog.text
    assert len(questions) == asked
    assert grants(fake_v1) == ["client_credentials"]


def test_login_needs_no_human_and_asserts_a_derived_subject(
        fake_v1, tmp_credentials, client_credentials):
    '''client_id=local:<derivation>, which RFC 6749 already registers.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    body = Client(tmp_credentials).login()

    assert body["access_token"] == "access-token-one"
    assert tmp_credentials.refresh_token == "refresh-token-one"
    # The access token is never written down.
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())
    sent = form(fake_v1.calls[-1].request.body)
    assert sent["grant_type"] == "client_credentials"
    assert sent["client_id"].startswith("local:")
    assert sent["machine_id_source"] in (
        "linux_machine_id", "macos_platform_uuid", "windows_machine_guid")


def test_no_fingerprint_no_access(fake_v1, tmp_credentials, client_credentials):
    '''With no machine id every such host would derive one subject.'''
    from siliconcompiler.remote.client import identity

    fake_v1.route(responses.POST, "auth/token", client_credentials)

    with mock.patch.object(identity, "machine_fingerprint", return_value=(None, "none")):
        with pytest.raises(RemoteError, match="no id to sign in with"):
            Client(tmp_credentials).login()

    assert not [call for call in fake_v1.calls if "auth/token" in call.request.url]


def test_the_subject_derivation_is_pinned():
    '''Changing the salt or the derivation is a silent identity migration:
    every user becomes a stranger on every server at once. The uid is in the
    subject (one identity per user on a login node); the machine label is
    not the subject.'''
    from siliconcompiler.remote.client import identity

    assert identity._SALT == b"siliconcompiler.remote.v1"
    if hasattr(os, "getuid"):
        assert identity._uid() == str(os.getuid())

    with mock.patch.object(identity, "machine_fingerprint",
                           return_value=("a-machine-id", "linux_machine_id")), \
         mock.patch.object(identity, "_uid", return_value="1000"):
        subject, label, source = identity.local_subject()

    assert subject == "ef75e01d65b55facdf7413b2840745d7:1000"
    assert label == "7eb20bb0b9607154b02dac185bb497d7"
    assert source == "linux_machine_id"


@pytest.mark.parametrize("lifetime,later", [
    (900, ["client_credentials"]),
    (1, ["client_credentials", "refresh_token"]),
], ids=["unexpired-token-is-read-with", "expired-token-refreshes"])
def test_a_first_command_enrolls_and_the_next_reads_with_its_token_or_refreshes(
        fake_v1, tmp_credentials, client_credentials, lifetime, later):
    '''`client_credentials` mints a new twelve-day token family each call, so a later
    process reads `/me` with the access token the store kept until it expires, and
    refreshes -- sending no scope -- only after, rather than rotating the pair for nothing.'''
    fake_v1.route(responses.POST, "auth/token", dict(client_credentials, expires_in=lifetime))
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()
    Client(Credentials(tmp_credentials.path)).me()

    assert grants(fake_v1) == later
    reads = [c.request for c in fake_v1.calls if c.request.method == "GET"
             and c.request.path_url.endswith("/me")]
    kept = "DPoP access-token-one"
    assert [read.headers["Authorization"] for read in reads] == [kept, kept]
    if len(later) > 1:
        refresh = [c.request for c in fake_v1.calls if c.request.method == "POST"][-1]
        assert "scope" not in form(refresh.body)


ME = {"id": "u1", "issuer": "local"}
EXPIRED = {"WWW-Authenticate": 'DPoP error="invalid_token"'}
ENROLL, REFRESH = "client_credentials", "refresh_token"


def _problem(slug, status, headers=None, path="me", method=responses.GET, **members):
    return (method, path, problem(slug, status, **members), status,
            "application/problem+json", headers)


def _oauth(error, headers=None, **members):
    return responses.POST, "auth/token", {"error": error, **members}, 400, \
        "application/json", headers


def _token(access="access-token-two"):
    return responses.POST, "auth/token", {"access_token": access}, 200, \
        "application/json", None


def _me():
    return responses.GET, "me", ME, 200, "application/json", None


def _nonce(slug, number, **headers):
    return _problem(slug, 401, {"DPoP-Nonce": number, **headers})


# `queue` is what the server answers after the call that is in the way; `grants` the
# token requests that made; `nonces` the proof's nonce on each request to a path.
@pytest.mark.parametrize("case", [
    pytest.param(dict(queue=[_problem("invalid-token", 401, EXPIRED), _token(), _me()],
                      grants=[ENROLL, REFRESH]), id="expired"),
    pytest.param(dict(queue=[(responses.GET, "me", "", 401, "text/plain", EXPIRED),
                             _token(), _me()],
                      grants=[ENROLL, REFRESH]), id="expired-by-the-header-alone"),
    # One refresh per request: a second `invalid-token` is the answer.
    pytest.param(dict(queue=[_problem("invalid-token", 401, EXPIRED)] * 3 + [_token()],
                      outcome="invalid-token", grants=[ENROLL, REFRESH]),
                 id="refused-again"),
    pytest.param(dict(queue=[_problem("a-type-from-later", 401,
                                      {"WWW-Authenticate": 'DPoP error="a_challenge_from_later"'})],
                      outcome=None, said=['error="a_challenge_from_later"'],
                      grants=[ENROLL]), id="unknown-challenge"),
    # The refresh token is the session that ended: log in again, never refresh.
    pytest.param(dict(queue=[_problem("session-ended", 401, reason="revoked"), _me()],
                      grants=[ENROLL, ENROLL]), id="session-ended"),
    # A bad proof is not a stale token, so nothing is refreshed; a clock over a minute
    # out is named from the server's `Date`, clear of each unit's boundary.
    pytest.param(dict(queue=[_problem("invalid-dpop-proof", 401)], offset=330,
                      outcome="invalid-dpop-proof", grants=[ENROLL],
                      said=[r"5m \d\ds behind", "clock"]), id="proof-clock-behind"),
    pytest.param(dict(queue=[_problem("invalid-dpop-proof", 401)], offset=-7530,
                      outcome="invalid-dpop-proof", grants=[ENROLL],
                      said=["2h 05m ahead", "clock"]), id="proof-clock-ahead"),
    pytest.param(dict(queue=[_problem("invalid-dpop-proof", 401)],
                      outcome="invalid-dpop-proof", grants=[ENROLL], unsaid=["clock is"]),
                 id="proof-clock-unknown"),
    # The clock is corrected and the request repeated whichever way the 401 says so.
    pytest.param(dict(queue=[(responses.GET, "me", {"error": "invalid_dpop_proof"}, 401,
                              "application/json", None), _me()],
                      offset=330, grants=[ENROLL], said=[r"5m \d\ds behind"]),
                 id="proof-clock-oauth-body"),
    pytest.param(dict(queue=[(responses.GET, "me", "", 401, "text/plain",
                              {"WWW-Authenticate": 'DPoP error="invalid_dpop_proof"'}),
                             _me()],
                      offset=330, grants=[ENROLL], said=[r"5m \d\ds behind"]),
                 id="proof-clock-challenge-only"),
    # A client that only refreshes loops on a nonce for ever; the nonce is sent once.
    pytest.param(dict(queue=[_nonce("dpop-nonce-required", "api-nonce"), _me()],
                      grants=[ENROLL], nonces=("/v1/me", [None, "api-nonce"])),
                 id="nonce-by-slug"),
    pytest.param(dict(queue=[_nonce("invalid-dpop-proof", "api-nonce", **{
                          "WWW-Authenticate": 'DPoP error="use_dpop_nonce"'}), _me()],
                      grants=[ENROLL], nonces=("/v1/me", [None, "api-nonce"])),
                 id="nonce-by-challenge"),
    pytest.param(dict(queue=[_nonce("dpop-nonce-required", "one"),
                             _nonce("dpop-nonce-required", "two")],
                      outcome="dpop-nonce-required", grants=[ENROLL],
                      nonces=("/v1/me", [None, "one"])), id="nonce-twice"),
    pytest.param(dict(logged_in=False, call="login",
                      queue=[_oauth("use_dpop_nonce", {"DPoP-Nonce": "token-nonce"}),
                             _token("access-token-one")],
                      grants=[ENROLL, ENROLL], nonces=("/auth/token", [None, "token-nonce"])),
                 id="token-nonce"),
    pytest.param(dict(logged_in=False, call="login",
                      queue=[_oauth("use_dpop_nonce", {"DPoP-Nonce": "one"}),
                             _oauth("use_dpop_nonce", {"DPoP-Nonce": "two"})],
                      outcome="oauth", said=["use_dpop_nonce"], grants=[ENROLL, ENROLL],
                      nonces=("/auth/token", [None, "one"])), id="token-nonce-twice"),
    # It has no access token for a refresh to repair.
    pytest.param(dict(logged_in=False, stored="whatever", call="refresh-grant",
                      queue=[_problem("invalid-token", 401, path="auth/token",
                                      method=responses.POST)],
                      outcome="invalid-token", grants=[REFRESH]), id="unauthenticated"),
    # Exactly one refresh and one enrolment, the new token replacing the dead one.
    pytest.param(dict(logged_in=False, stored="long-dead", queue=[
        _oauth("invalid_grant", reason="revoked"), _token("access-token-one"), _me()],
        grants=[REFRESH, ENROLL]), id="dead-refresh-revoked"),
    pytest.param(dict(logged_in=False, stored="long-dead", queue=[
        _oauth("invalid_grant"), _token("access-token-one"), _me()],
        grants=[REFRESH, ENROLL]), id="dead-refresh-no-reason"),
    pytest.param(dict(logged_in=False, stored="long-dead", queue=[
        _oauth("invalid_grant", reason="reused"), _token("access-token-one"), _me()],
        grants=[REFRESH, ENROLL], said=["sc-config remote rotate-key", "used elsewhere"]),
        id="dead-refresh-reused"),
])
def test_a_refusal_at_authentication_is_acted_on_by_what_it_says(
        request, fake_v1, tmp_credentials, client_credentials, caplog, case):
    '''A refusal is read by its slug, challenge or OAuth `error`, not its status: refresh
    once, log in again where the session ended, repeat a nonce once, and stop on the rest.'''
    import email.utils
    import time as clock

    case = {"logged_in": True, "stored": None, "call": "me", "outcome": "ok", "said": (),
            "unsaid": (), "nonces": None, "offset": None, **case}
    if case["logged_in"]:
        client = request.getfixturevalue("logged_in")
    else:
        if case["stored"]:
            tmp_credentials.save_tokens({"refresh_token": case["stored"]})
        client = Client(tmp_credentials)
    for index, (method, path, body, status, content_type, headers) in enumerate(case["queue"]):
        if status == 200:
            body = {**client_credentials, **body} if path == "auth/token" else body
        if index == 0 and case["offset"] is not None:
            headers = {**(headers or {}), "Date": email.utils.formatdate(
                clock.time() + case["offset"], usegmt=True)}
        fake_v1.route(method, path, body, status=status, content_type=content_type,
                      headers=headers)
    call = {"me": client.me, "login": client.login,
            "refresh-grant": lambda: client.transport.login(
                {"grant_type": "refresh_token", "refresh_token": "whatever"})}[case["call"]]

    with caplog.at_level("WARNING"):
        if case["outcome"] == "ok":
            call()
            said = caplog.text
            assert tmp_credentials.refresh_token == "refresh-token-one"
            assert tmp_credentials.access_token()[0] == client.transport.access_token is not None
        else:
            with pytest.raises(RemoteError) as raised:
                call()
            said = str(raised.value)
            if case["outcome"] == "oauth":
                assert not isinstance(raised.value, ServerProblem)
            else:
                assert raised.value.slug == case["outcome"]

    assert grants(fake_v1) == case["grants"]
    for fragment in case["said"]:
        assert re.search(fragment, said), said
    assert not any(fragment in said for fragment in case["unsaid"])
    if case["nonces"]:
        path, expected = case["nonces"]
        assert [claims(c.request.headers["DPoP"]).get("nonce") for c in fake_v1.calls
                if c.request.url.endswith(path)] == expected


@pytest.mark.parametrize("body,status,extra,said,unsaid", [
    pytest.param(
        problem("limit-exceeded", 429, limit="concurrent_jobs", job_ids=["a", "b"],
                trace_id="a" * 32, detail="four already running" + EVIL),
        429, {},
        ["Limit exceeded (429): four already running", "limit: concurrent_jobs",
         "job_ids: a b", "refills", "trace " + "a" * 32], [], id="detail-members-and-trace"),
    pytest.param(problem("feature-unsupported", 501, feature="projects"), 501, {},
                 ["feature: projects", "does not offer that"], [], id="feature"),
    pytest.param(
        problem("software-unavailable", 422, reason="unavailable", unresolved=[
            {"kind": "tools", "name": "openroad", "requirement": [">=24.3.2011", "==2.0"],
             "available": ["2.1.0"]},
            {"kind": "tools", "name": "magic", "requirement": [], "available": []},
            {"kind": "python", "name": "za-sclib", "requirement": ["==0.1.80"],
             "available": ["0.1.80"]},
            {"kind": "class", "name": "mytasks/MyTask", "requirement": [], "available": []},
            {"kind": "package", "name": "numpy", "requirement": ["==1.*"], "available": []}]),
        422, {},
        ["reason: unavailable", "tool openroad >=24.3.2011 or ==2.0 (available: 2.1.0)",
         "tool magic any version (available: none)",
         "python za-sclib ==0.1.80 (available: 0.1.80)", "task class mytasks/MyTask",
         "package numpy ==1.* (available: none)", "Ask for a version this server has"],
        [], id="software-by-kind"),
    pytest.param(
        problem("software-unavailable", 422, reason="unavailable", unresolved=[
            {"kind": "interpreter", "name": "python", "requirement": ["==3.12.*"],
             "available": ["3.11.9"]}]),
        422, {},
        ["interpreter python ==3.12.* (available: 3.11.9)",
         "No image here runs the Python this machine does"], ["Ask for a version"],
        id="software-interpreter"),
    # Each document by its title where known, else its id; anything else names nothing.
    pytest.param(problem("terms-not-accepted", 403,
                         blocked_by=["tos", "gf22-nda", {"id": "export"}, ""]),
                 403, {"titles": {"tos": "Terms of Service"}},
                 ["sign Terms of Service", "sign gf22-nda", "Sign each document"],
                 ["sign {", "sign export"], id="blocked-by"),
    pytest.param(problem("archive-rejected", 422, reason="a-reason-from-later"), 422, {},
                 ["reason: a-reason-from-later", "Fix what the reason names, in a new job."],
                 [], id="unknown-reason"),
    pytest.param(problem("entitlement-denied", 403, resource_kind="pdk", resource="gf12"),
                 403, {}, ["resource: gf12", "resource_kind: pdk", "Ask for a grant"], [],
                 id="entitlement"),
    pytest.param(problem("entitlement-denied", 403, resource_kind="capability",
                         resource="a-capability-from-later"),
                 403, {}, ["Ask the deployment for that grant"], [], id="unknown-capability"),
    # By name, never as `resource_kind: None`.
    pytest.param(problem("resource-unavailable", 422, resource="secret"), 422, {},
                 ["resource: secret", "cannot be sent it"], ["resource_kind", "None"],
                 id="resource-without-a-kind"),
    # Never an HTTP response, so no status; a limit in `detail` changes nothing.
    pytest.param(problem("run-failed", None, detail="place/0 exceeded its time limit"),
                 None, {}, ["exceeded its time limit", "Read the failing node's log"],
                 ["(None)"], id="no-status"),
    # An unknown type, or one outside the registry, is acted on by its status.
    pytest.param(problem("a-type-from-later", 422), 422, {},
                 ["retrying it unchanged will not help"], [], id="unknown-type"),
    pytest.param({"title": "Bad Gateway"}, 502, {}, ["Bad Gateway (502)", "try again later"],
                 [], id="untyped-5xx"),
    pytest.param({"type": "https://elsewhere.test/server-errors/limit-exceeded",
                  "title": "Refused"}, 429, {}, ["Wait and retry."], ["refills"],
                 id="type-outside-the-registry"),
])
def test_a_refusal_renders_without_opening_a_url(body, status, extra, said, unsaid):
    '''The type pages are static, so the client holds the only copy of the specific
    failure: the discriminator, the next step and the trace, each cleaned for a terminal.'''
    refusal = ServerProblem(body, status, **extra)
    rendered = str(refusal)
    slug = body.get("type", "")[len(TYPE_BASE):] if body.get("type", "").startswith(
        TYPE_BASE) else None
    slug = slug if slug in REGISTERED else None

    assert refusal.slug == slug
    for name in set(body) - {"type", "title", "status"}:
        assert refusal.member(name) == body[name]
    if slug:
        assert f"server-errors/{slug}" in rendered
    for fragment in said:
        assert fragment in rendered, rendered
    assert not any(fragment in rendered for fragment in unsaid)
    assert "\x07" not in rendered and "\x1b]" not in rendered


def test_a_changed_identity_is_reported_rather_than_read_as_lost_jobs(
        fake_v1, tmp_credentials, client_credentials, caplog):
    '''A reimage, container or changed uid replaces the principal; without
    the persisted id, "my jobs were deleted" looks the same.'''
    caplog.set_level(logging.WARNING)
    tmp_credentials.set_user_id("the-old-me")
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "the-new-me", "issuer": "local"})

    Client(tmp_credentials).me()

    assert "different user" in caplog.text
    assert tmp_credentials.user_id == "the-new-me"


@pytest.mark.parametrize("content_type,body,said", [
    ("application/json", problem("archive-rejected", 422), ["(422)"]),
    ("application/problem+json",
     {"title": "Refused here", "detail": "by the gateway", "trace_id": "a" * 32,
      "instance": "/v1/me"},
     ["Refused here (422): by the gateway", "trace " + "a" * 32]),
], ids=["json-with-a-type", "problem-without-one"])
def test_only_problem_json_names_a_condition(logged_in, fake_v1, content_type, body, said):
    '''A `type` counts only under its own content type; a problem without one
    keeps everything it said.'''
    fake_v1.route(responses.GET, "me", body, status=422, content_type=content_type)

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.slug is None and raised.value.status == 422
    for fragment in said:
        assert fragment in str(raised.value)
    if "instance" in body:
        assert raised.value.member("instance") == "/v1/me"


def test_devices_are_listed_across_pages_and_revoked(fake_v1, logged_in):
    fake_v1.route(responses.GET, "devices", {"items": [{"id": "d1", "current": True}]},
                  headers={"Link": f'<{V1_URL}/devices?cursor=c2>; rel="next"'})
    fake_v1.route(responses.GET, "devices", {"items": [{"id": "d2"}]})

    assert [device["id"] for device in logged_in.devices()] == ["d1", "d2"]
    assert fake_v1.calls[-1].request.url.endswith("cursor=c2")

    fake_v1.route(responses.DELETE, "devices/d1", "", status=204)
    logged_in.revoke_device("d1")

    assert fake_v1.calls[-1].request.method == "DELETE"


@pytest.mark.parametrize("answer", [
    {"body": "", "status": 204},
    {"body": problem("session-ended", 401, reason="revoked"), "status": 401,
     "content_type": "application/problem+json"},
    {"body": problem("invalid-token", 401), "status": 401,
     "content_type": "application/problem+json",
     "headers": {"WWW-Authenticate": 'DPoP error="invalid_token"'}},
], ids=["live", "already-dead", "token-refused"])
def test_logout_forgets_the_session(fake_v1, logged_in, tmp_credentials, answer):
    '''Even one already gone: the remaining job is local, and leaving never
    starts a refresh or a login.'''
    fake_v1.route(responses.POST, "auth/revoke", **answer)

    logged_in.logout()

    assert tmp_credentials.refresh_token is None
    assert len([c for c in fake_v1.calls if c.request.url.endswith("/auth/token")]) == 1


@pytest.mark.parametrize("software,said,unsaid", [
    (None, ["This server runs siliconcompiler 0.38.9"], []),
    ({"python": {"siliconcompiler": ["9.9.9"]}, "tools": {}},
     ["which is not one of them", "before anything is uploaded"], []),
    ({"python": {}, "tools": {}}, [], ["This server runs"]),
], ids=["runs", "not-listed", "names-none"])
def test_configure_says_what_the_server_runs(fake_v1, capabilities, tmp_credentials,
                                             client_credentials, caplog, software, said,
                                             unsaid):
    '''`-configure` reports the software the server runs, and does not second-guess a server that
    names none. A new server is not identity drift, so the old principal is forgotten.'''
    if software is not None:
        capabilities["software"] = software
        fake_v1.replace(responses.GET, "", capabilities)
    tmp_credentials.set_user_id("who-the-old-server-called-me")
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-new", "issuer": "local"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).configure_server(server=V1_URL.rsplit("/v1", 1)[0])

    assert tmp_credentials.user_id == "u-new"
    assert all(line in caplog.text for line in said)
    assert not any(line in caplog.text for line in unsaid)


OTHER_URL = "https://other.test/v1"


def test_switching_servers_asks_nothing_and_keeps_each_session(
        fake_v1, capabilities, tmp_credentials, client_credentials, monkeypatch):
    '''Each server keeps its own entry, so a switch overwrites nothing; switching
    back refreshes the session that server already has.'''
    from conftest import FakeV1

    monkeypatch.setattr("siliconcompiler.remote.client._ask",
                        lambda *args, **kwargs: pytest.fail("asked a question"))
    tmp_credentials.save_tokens({"refresh_token": "refresh-for-the-first"})
    other = FakeV1(fake_v1._mock, OTHER_URL)
    other.route(responses.GET, "", capabilities)
    other.route(responses.POST, "auth/token",
                {**client_credentials, "refresh_token": "refresh-for-the-other"})
    other.route(responses.GET, "me", {"id": "u-other", "issuer": "local"})
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).configure_server(server=OTHER_URL.rsplit("/v1", 1)[0])
    assert tmp_credentials.server == OTHER_URL
    assert tmp_credentials.refresh_token == "refresh-for-the-other"

    Client(tmp_credentials).configure_server(server=V1_URL.rsplit("/v1", 1)[0])
    assert tmp_credentials.server == V1_URL
    assert grants(fake_v1)[-1] == "refresh_token"


@pytest.mark.parametrize("configured", [True, False], ids=["switching", "first"])
@pytest.mark.parametrize("failure", ["unreachable", "login-refused"])
def test_a_server_that_cannot_be_used_is_not_saved(fake_v1, capabilities, configured,
                                                   failure):
    '''Configuring either works or changes nothing: the default stays what it was,
    and the new server gets no entry.'''
    from conftest import FakeV1

    credentials = Credentials(Path("sc-home/auth/remote.json"))
    if configured:
        credentials.set_server(V1_URL.rsplit("/v1", 1)[0])
    if failure == "login-refused":
        other = FakeV1(fake_v1._mock, OTHER_URL)
        other.route(responses.GET, "", capabilities)
        other.route(responses.POST, "auth/token", {"error": "invalid_client"}, status=401)

    with pytest.raises(RemoteError):
        Client(credentials).configure_server(server=OTHER_URL.rsplit("/v1", 1)[0])

    assert credentials.server == (V1_URL if configured else None)
    assert not credentials.knows(OTHER_URL)


def test_use_server_switches_among_the_servers_configured_here(fake_v1, tmp_credentials,
                                                               caplog):
    '''Nothing is sent, and each server's session comes back with it; a server not
    configured here is refused, naming -configure.'''
    tmp_credentials.save_tokens({"refresh_token": "refresh-for-the-first"})
    tmp_credentials.set_server(OTHER_URL.rsplit("/v1", 1)[0])
    tmp_credentials.save_tokens({"refresh_token": "refresh-for-the-other"})
    client = Client(tmp_credentials)

    caplog.set_level(logging.INFO)
    cli.print_configuration(client)
    assert f"Also configured (sc-config remote use): {V1_URL}" in caplog.text

    client.use_server(V1_URL.rsplit("/v1", 1)[0])
    assert (tmp_credentials.server, client.base_url) == (V1_URL, V1_URL)
    assert tmp_credentials.refresh_token == "refresh-for-the-first"

    with pytest.raises(RemoteError, match="sc-config remote configure https://new.test"):
        client.use_server("https://new.test")
    assert tmp_credentials.server == V1_URL
    assert not fake_v1.calls


def test_a_named_server_is_acted_for_and_a_logout_forgets_it(
        fake_v1, tmp_credentials, client_credentials, caplog):
    '''Naming a server leaves the default alone; a logout revokes its session and
    removes it here, its headers with it, and a default it was stays unset.'''
    from conftest import FakeV1

    other = FakeV1(fake_v1._mock, OTHER_URL)
    for server in (fake_v1, other):
        server.route(responses.POST, "auth/token", client_credentials)
        server.route(responses.POST, "auth/revoke", {})
    tmp_credentials.save_tokens({"refresh_token": "r1"})
    tmp_credentials.set_server(OTHER_URL.rsplit("/v1", 1)[0])
    tmp_credentials.save_tokens({"refresh_token": "r2"})
    tmp_credentials.set_header("X-Edge", "other's")
    tmp_credentials.set_server(V1_URL.rsplit("/v1", 1)[0])
    client = Client(tmp_credentials)

    client.select(OTHER_URL)
    assert (client.base_url, tmp_credentials.headers()) == (OTHER_URL, {"X-Edge": "other's"})
    assert Credentials(tmp_credentials.path).server == V1_URL

    client.select(None)
    with caplog.at_level(logging.INFO):
        client.logout()
    assert f"choose one of {OTHER_URL}" in caplog.text
    stored = Credentials(tmp_credentials.path)
    assert (stored.server, stored.servers()) == (None, [OTHER_URL])

    client.select(OTHER_URL)
    client.logout()
    assert Credentials(tmp_credentials.path).servers() == []
    assert [c.request.url for c in fake_v1.calls if c.request.url.endswith("/revoke")] == \
        [f"{V1_URL}/auth/revoke", f"{OTHER_URL}/auth/revoke"]
