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
from siliconcompiler.remote.client.errors import describe
from siliconcompiler.remote.client.transport import join_url, normalize_server

from conftest import V1_URL, problem


def _form(body):
    from urllib.parse import parse_qs

    if isinstance(body, bytes):
        body = body.decode()
    return {k: v[0] for k, v in parse_qs(body).items()}


def _grants(fake_v1):
    return [_form(c.request.body)["grant_type"]
            for c in fake_v1.calls if c.request.method == "POST"]


def _refused(fake_v1, path, slug, status, headers=None, method=responses.GET, **members):
    fake_v1.route(method, path, problem(slug, status, **members), status=status,
                  content_type="application/problem+json", headers=headers)


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


def test_configuring_an_ipv6_server_keeps_its_port():
    '''As `sc-remote -configure -server` splits it.'''
    from siliconcompiler.remote.client import _split_address

    address, port, had_credentials = _split_address("https://[::1]:8000")

    assert (address, port, had_credentials) == ("https://[::1]", 8000, False)
    assert normalize_server(address, port) == "https://[::1]:8000/v1"
    assert _split_address("https://me:secret@example.com")[2] is True


def test_a_client_without_a_server_builds_and_says_so(caplog):
    '''Constructing must not raise, or `sc-remote -configure` could not fix it.'''
    caplog.set_level(logging.INFO)
    client = Client(Credentials(Path("sc-home/auth/remote.json")))
    client.print_configuration()

    assert client.base_url is None
    assert "Server: not configured" in caplog.text
    with pytest.raises(RemoteError, match="No remote server address is configured"):
        client.capabilities()
    with pytest.raises(RemoteError, match="sc-remote -configure"):
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
    # 🔴 A closed set of buckets, and `siliconcompiler` REQUIRED in `python`.
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
    '''🔴 The endpoint serves `fail` as a 503, and nothing answering 503 here
    is serving, whatever it sends.'''
    fake_v1.route(responses.GET, "healthz", body, status=status, content_type=content_type)

    assert Client(tmp_credentials).health() == {"status": expected}
    assert "Authorization" not in fake_v1.calls[-1].request.headers


def test_the_deployment_report_is_what_the_server_says_it_is(
        fake_v1, tmp_credentials, capabilities, caplog):
    '''🔴 Unauthenticated, so it prints before enrolment and for a server
    that is down. Limits in readable units; null is unlimited, not zero.'''
    capabilities["limits"]["concurrent_jobs"] = None
    fake_v1.replace(responses.GET, "", capabilities)
    _healthy(fake_v1)

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).print_deployment()

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
    client.print_deployment()
    client.print_deployment()

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
    '''A `terms` entry as surface D309 has it: `can_decide`, and no URL.'''
    return {"id": "tos", "title": "Terms of Service", "scope": {"applies_to": "service"},
            "version": "2026-09-01", "accepted_at": "2026-09-02T00:00:00Z",
            "declined_at": None, "can_decide": can_decide,
            "upcoming": {"version": "2026-11-01", "effective_at": "2026-11-01T00:00:00Z",
                         "accepted_at": accepted_at}}


def asked_for_pages(fake_v1):
    '''Each body this client sent endpoint 6.'''
    return [json.loads(c.request.body or b"{}") for c in fake_v1.calls
            if c.request.url.endswith("/v1/auth/browser")]


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


def test_an_upcoming_version_is_named_once_per_session_and_never_accepted(
        logged_in, fake_v1, caplog, monkeypatch):
    '''🔴 Named before it takes effect; the client never accepts, and asks for
    no page it will not open.'''
    _asked(monkeypatch)
    fake_v1.route(responses.GET, "me", me_body(terms_entry()))
    caplog.set_level(logging.INFO)

    logged_in.me()
    logged_in.me()

    named = [record.message for record in caplog.records if "2026-11-01" in record.message]
    assert len(named) == 1
    assert "Terms of Service" in named[0]
    assert "2026-11-01T00:00:00Z" in named[0]
    assert "accepted early, on its page in this server's portal" in caplog.text
    assert asked_for_pages(fake_v1) == []
    assert not [c for c in fake_v1.calls if c.request.method != "GET"
                and "/auth/token" not in c.request.url]


def test_an_accepted_upcoming_version_is_not_mentioned(logged_in, fake_v1, caplog):
    fake_v1.route(responses.GET, "me",
                  me_body(terms_entry(accepted_at="2026-10-01T00:00:00Z")))
    caplog.set_level(logging.INFO)

    logged_in.me()

    assert "2026-11-01" not in caplog.text


def test_on_a_terminal_the_page_is_offered_and_opened_only_when_asked(
        logged_in, fake_v1, monkeypatch):
    answers = iter(["n", "y"])
    _asked(monkeypatch, lambda question: next(answers), tty=True)
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    fake_v1.route(responses.GET, "me", me_body(terms_entry()))
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://portal.test/enter?token=t1", "expires_at": None})

    logged_in.me()
    assert opened == []
    assert asked_for_pages(fake_v1) == []

    # Every time in the check command.
    logged_in.remind_terms(me_body(terms_entry()), always=True)
    assert asked_for_pages(fake_v1) == [{"terms_id": "tos"}]
    assert opened == ["https://portal.test/enter?token=t1"]


@pytest.mark.parametrize("can_decide,ci", [(False, False), (True, True)],
                         ids=["page-cannot-decide", "ci"])
def test_an_upcoming_version_is_only_reported_where_no_page_is_offered(
        logged_in, fake_v1, monkeypatch, caplog, can_decide, ci):
    _asked(monkeypatch, tty=True, ci=ci)
    fake_v1.route(responses.GET, "me", me_body(terms_entry(can_decide=can_decide)))
    caplog.set_level(logging.INFO)

    logged_in.me()

    assert "2026-11-01" in caplog.text
    assert asked_for_pages(fake_v1) == []
    if not can_decide:
        assert "accepted early" not in caplog.text


def test_login_needs_no_human_and_asserts_a_derived_subject(
        fake_v1, tmp_credentials, client_credentials):
    '''client_id=local:<derivation>, which RFC 6749 already registers.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)

    body = Client(tmp_credentials).login()

    assert body["access_token"] == "access-token-one"
    assert tmp_credentials.refresh_token == "refresh-token-one"
    # 🔴 The access token is never written down.
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())
    sent = _form(fake_v1.calls[-1].request.body)
    assert sent["grant_type"] == "client_credentials"
    assert sent["client_id"].startswith("local:")
    assert sent["machine_id_source"] in (
        "linux_machine_id", "macos_platform_uuid", "windows_machine_guid")


def test_no_fingerprint_no_access(fake_v1, tmp_credentials, client_credentials):
    '''🔴 With no machine id every such host would derive one subject.'''
    from siliconcompiler.remote.client import identity

    fake_v1.route(responses.POST, "auth/token", client_credentials)

    with mock.patch.object(identity, "machine_fingerprint", return_value=(None, "none")):
        with pytest.raises(RemoteError, match="no id to sign in with"):
            Client(tmp_credentials).login()

    assert not [call for call in fake_v1.calls if "auth/token" in call.request.url]


def test_the_subject_derivation_is_pinned():
    '''🔴 Changing the salt or the derivation is a silent identity migration:
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


def test_a_first_command_enrolls_and_the_next_refreshes(
        fake_v1, tmp_credentials, client_credentials):
    '''🔴 `client_credentials` mints a new twelve-day token family each call,
    so a later process must use `refresh_token` -- and send no scope.'''
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    Client(tmp_credentials).me()
    Client(Credentials(tmp_credentials.path)).me()

    assert _grants(fake_v1) == ["client_credentials", "refresh_token"]
    refresh = [c.request for c in fake_v1.calls if c.request.method == "POST"][-1]
    assert "scope" not in _form(refresh.body)


@pytest.mark.parametrize("reason", ["revoked", None, "reused"])
def test_a_dead_refresh_token_falls_back_to_enrolling_once(
        fake_v1, tmp_credentials, client_credentials, caplog, reason):
    '''🔴 Exactly one refresh and one enrolment: a refused refresh once
    recursed through login() for hundreds of real round trips. The new token
    replaces the dead one; `reused` also says to rotate the key.'''
    tmp_credentials.save_tokens({"refresh_token": "long-dead"})
    fake_v1.route(responses.POST, "auth/token",
                  {"error": "invalid_grant", **({"reason": reason} if reason else {})},
                  status=400)
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    with caplog.at_level("WARNING"):
        assert Client(tmp_credentials).me()["id"] == "u1"

    assert _grants(fake_v1) == ["refresh_token", "client_credentials"]
    assert tmp_credentials.refresh_token == "refresh-token-one"
    if reason == "reused":
        assert "sc-remote -rotate_key" in caplog.text
        assert "used elsewhere" in caplog.text


def test_an_expired_token_is_refreshed_silently(logged_in, fake_v1, tmp_credentials,
                                                client_credentials):
    _refused(fake_v1, "me", "invalid-token", 401,
             headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})
    fake_v1.route(responses.POST, "auth/token",
                  {**client_credentials, "access_token": "access-token-two"})
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert logged_in.me()["id"] == "u1"
    assert tmp_credentials.refresh_token == "refresh-token-one"
    assert "access_token" not in json.loads(tmp_credentials.path.read_text())


def test_a_dead_session_is_logged_into_again_never_refreshed(logged_in, fake_v1):
    '''The refresh token is the session that ended.'''
    _refused(fake_v1, "me", "session-ended", 401, reason="revoked")
    fake_v1.route(responses.GET, "me", {"id": "u1", "issuer": "local"})

    assert logged_in.me()["id"] == "u1"
    assert _grants(fake_v1) == ["client_credentials", "client_credentials"]


# Clear of each unit's boundary: `Date` has one-second resolution.
@pytest.mark.parametrize("offset,said", [(330, r"5m \d\ds behind"), (-7530, "2h 05m ahead"),
                                         (20, None), (None, None)])
def test_a_refused_proof_fails_and_says_when_the_clock_is_off(logged_in, fake_v1,
                                                              offset, said):
    '''🔴 Surface D167: a bad proof is not a stale token, so nothing is
    refreshed; a clock over a minute out is named from the server's `Date`.'''
    import email.utils
    import time as clock

    headers = None if offset is None else \
        {"Date": email.utils.formatdate(clock.time() + offset, usegmt=True)}
    _refused(fake_v1, "me", "invalid-dpop-proof", 401, headers=headers)

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.slug == "invalid-dpop-proof"
    assert _grants(fake_v1) == ["client_credentials"]
    if said:
        assert re.search(said, str(raised.value)) and "clock" in str(raised.value)
    else:
        assert "clock is" not in str(raised.value)


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


@pytest.mark.parametrize("body,status,said", [
    (problem("limit-exceeded", 429, limit="concurrent_jobs", detail="four already running",
             trace_id="a" * 32),
     None, ["four already running", "limit: concurrent_jobs", "refills", "trace " + "a" * 32]),
    (problem("feature-unsupported", 501, feature="device_grant"), None,
     ["feature: device_grant"]),
    (problem("archive-rejected", 422, reason="expanded_bytes"), None,
     ["reason: expanded_bytes"]),
    (problem("archive-rejected", 422, reason="a-reason-from-later"), None,
     ["Fix what the reason names, in a new job."]),
    ({"title": "Bad Gateway"}, 502, ["try again later"]),
], ids=["detail-and-trace", "feature", "reason", "unknown-reason", "untyped-5xx"])
def test_a_refusal_renders_without_opening_a_url(body, status, said):
    '''The type pages are static, so the client holds the only copy of the
    specific failure: the discriminator, the next step and the trace.'''
    rendered = describe(body, status) if status else describe(body)

    for fragment in said:
        assert fragment in rendered


@pytest.mark.parametrize("body,status,content_type", [
    ("<html><head><title>502 Bad Gateway</title></head>"
     "<body><h1>502 Bad Gateway</h1></body></html>", 502, "text/html"),
    ("", 503, "text/plain"),
], ids=["proxy-html", "empty"])
def test_a_non_problem_error_body_renders_rather_than_throwing(logged_in, fake_v1, body,
                                                               status, content_type):
    '''problem+json is promised only for what a handler produced.'''
    fake_v1.route(responses.GET, "me", body, status=status, content_type=content_type)

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.status == status
    assert raised.value.slug is None
    assert str(raised.value) and "<html>" not in str(raised.value)
    if body:
        assert "502" in str(raised.value)


def test_an_unknown_type_is_acted_on_by_its_status(fake_v1, logged_in):
    '''A 4xx from a later registry is still not worth repeating.'''
    _refused(fake_v1, "me", "a-type-from-later", 422)

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.slug == "a-type-from-later"
    assert "retrying it unchanged will not help" in str(raised.value)


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
], ids=["live", "already-dead"])
def test_logout_forgets_the_session(fake_v1, logged_in, tmp_credentials, answer):
    '''Even one already gone: the remaining job is local.'''
    fake_v1.route(responses.POST, "auth/revoke", **answer)

    logged_in.logout()

    assert tmp_credentials.refresh_token is None


@pytest.mark.parametrize("software,said,unsaid", [
    (None, ["This server runs siliconcompiler 0.38.9"], []),
    ({"python": {"siliconcompiler": ["9.9.9"]}, "tools": {}},
     ["which is not one of them", "before anything is uploaded"], []),
    ({"python": {}, "tools": {}}, [], ["This server runs"]),
], ids=["runs", "not-listed", "names-none"])
def test_configure_says_what_the_server_runs(fake_v1, capabilities, tmp_credentials,
                                             client_credentials, caplog, software, said,
                                             unsaid):
    '''🔴 Visible while somebody watches, not at the first submit; the server
    still decides. A server naming no software is not second-guessed. A new
    server is not identity drift, so the old principal is forgotten.'''
    if software is not None:
        capabilities["software"] = software
        fake_v1.replace(responses.GET, "", capabilities)
    tmp_credentials.set_user_id("who-the-old-server-called-me")
    fake_v1.route(responses.POST, "auth/token", client_credentials)
    fake_v1.route(responses.GET, "me", {"id": "u-new", "issuer": "local"})

    caplog.set_level(logging.INFO)
    Client(tmp_credentials).configure_server(
        server=V1_URL.rsplit("/v1", 1)[0], clobber=True, prompt=False)

    assert tmp_credentials.user_id == "u-new"
    assert all(line in caplog.text for line in said)
    assert not any(line in caplog.text for line in unsaid)


def test_an_unauthenticated_request_never_refreshes(fake_v1, tmp_credentials):
    '''It has no access token for a refresh to repair.'''
    tmp_credentials.save_tokens({"refresh_token": "whatever"})
    _refused(fake_v1, "auth/token", "invalid-token", 401, method=responses.POST)

    client = Client(tmp_credentials)
    with pytest.raises(ServerProblem):
        client.transport.login({"grant_type": "refresh_token",
                                "refresh_token": "whatever"})

    assert len([c for c in fake_v1.calls if c.request.method == "POST"]) == 1


def test_a_refresh_cannot_start_inside_a_refresh(fake_v1, tmp_credentials):
    '''Impossible by construction: that loop costs the server.'''
    tmp_credentials.save_tokens({"refresh_token": "a-token"})
    client = Client(tmp_credentials)

    client.transport._refreshing = True
    assert client.transport.refresh() is False
    assert not fake_v1.calls[1:]        # nothing beyond discovery
