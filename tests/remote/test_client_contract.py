import json

import pytest
import responses

from conftest import problem

from siliconcompiler.remote import Client, ServerProblem
from siliconcompiler.remote.client import OAuthRefusal
from siliconcompiler.remote.client.errors import describe


# The client half of the contract's behaviour tests (contract.md §6), against
# canned answers: the rules the rest of the suite does not already hold.

ORIGIN = "https://sc-server.test"


###########################
# The nonce challenge: retried once, in both shapes
###########################

def test_a_second_nonce_challenge_is_the_answer(logged_in, fake_v1):
    for nonce in ("one", "two"):
        fake_v1.route(responses.GET, "me", problem("dpop-nonce-required", 401),
                      status=401, content_type="application/problem+json",
                      headers={"DPoP-Nonce": nonce})

    with pytest.raises(ServerProblem) as raised:
        logged_in.me()

    assert raised.value.slug == "dpop-nonce-required"
    assert len([c for c in fake_v1.calls if c.request.url.endswith("/v1/me")]) == 2


def test_a_second_nonce_challenge_at_the_token_endpoint_is_the_answer(
        fake_v1, tmp_credentials):
    for nonce in ("one", "two"):
        fake_v1.route(responses.POST, "auth/token", {"error": "use_dpop_nonce"},
                      status=400, headers={"DPoP-Nonce": nonce})

    with pytest.raises(Exception):
        Client(tmp_credentials).login()

    assert len([c for c in fake_v1.calls if c.request.url.endswith("/auth/token")]) == 2


###########################
# What a followed redirect carries
###########################

def test_a_same_origin_signed_route_gets_the_operator_headers_and_no_session(
        logged_in, fake_v1, tmp_credentials, tmp_path):
    '''The artifact 303 on `sc-server`'s own host: the operator's header goes,
    because the edge in front of the host wants it, and the session never
    does, since the signature is the credential.'''
    tmp_credentials.set_header("CF-Access-Client-Id", "id")
    fake_v1.route(responses.GET, "jobs/J/artifacts/A", "", status=303,
                  headers={"Location": f"{ORIGIN}/storage/artifact/J/A?sig=1"})
    fake_v1.elsewhere(responses.GET, f"{ORIGIN}/storage/artifact/J/A", "bytes",
                      content_type="application/octet-stream")

    logged_in.fetch_artifact("J", "A", tmp_path / "a.bin")

    signed = fake_v1.calls[-1].request
    assert signed.headers["CF-Access-Client-Id"] == "id"
    assert "Authorization" not in signed.headers and "DPoP" not in signed.headers


###########################
# Unknown values
###########################

def test_an_unknown_response_member_is_ignored(logged_in, fake_v1, capabilities,
                                               nop_project, monkeypatch):
    from siliconcompiler.remote.client.run import RemoteRun

    monkeypatch.setattr("siliconcompiler.remote.client.run.time.sleep", lambda s: None)
    published = dict(capabilities, a_member_from_later={"anything": [1, 2]})
    fake_v1.replace(responses.GET, "", published)
    fake_v1.route(responses.GET, "jobs/j1", {
        "id": "j1", "state": "completed", "terminal": True, "nodes": [],
        "progress": {"total_count": 0, "completed_count": 0, "failed_count": 0},
        "a_member_from_later": {"x": 1}})

    assert logged_in.capabilities()["api_version"] == "v1"
    RemoteRun(nop_project, logged_in)._poll("j1")


###########################
# Every OAuth `error`, at both OAuth endpoints
###########################

@pytest.mark.parametrize("path", ["auth/token", "auth/device"])
@pytest.mark.parametrize("body", [
    {"error": "invalid_grant", "reason": "revoked"},
    {"error": "invalid_grant", "reason": "reused"},
    {"error": "invalid_grant", "reason": "expired"},
    {"error": "invalid_grant", "reason": "deactivated"},
    {"error": "invalid_grant"},
    {"error": "invalid_client", "error_description": "bound to a different key"},
    {"error": "unsupported_grant_type"},
    {"error": "invalid_scope"},
    {"error": "invalid_dpop_proof"},
])
def test_every_oauth_error_is_read_for_error_and_reason(fake_v1, logged_in, path, body):
    '''The OAuth shape: `error`, then `reason`, never `type`.'''
    fake_v1.route(responses.POST, path, body, status=400)

    with pytest.raises(OAuthRefusal) as raised:
        logged_in.transport.request("POST", path, data={"grant_type": "x"},
                                    authenticated=False, oauth=True)

    assert (raised.value.error, raised.value.reason) == (body["error"], body.get("reason"))


###########################
# Bringing results home
###########################

def test_server_text_loses_its_control_characters_and_keeps_its_colour():
    text = describe(problem("run-failed", None,
                            detail="bad\x00 bell\x07 clear\x1b[2J red\x1b[31mX\x1b[0m\ttab"))

    assert "\x00" not in text and "\x07" not in text and "\x1b[2J" not in text
    assert "\x1b[31mX\x1b[0m" in text and "\ttab" in text


def test_a_notice_loses_its_control_characters(logged_in, fake_v1, capabilities, caplog):
    import logging

    fake_v1.replace(responses.GET, "", dict(capabilities, notices=[
        {"level": "info", "message": "down\x1b]0;owned\x07 soon", "starts_at": None,
         "ends_at": None}]))
    caplog.set_level(logging.INFO)

    logged_in.capabilities()

    line, = [record.message for record in caplog.records if "Notice" in record.message]
    assert "\x07" not in line and "\x1b]" not in line


def test_an_http_url_from_a_deployment_that_authenticates_is_printed_not_opened(
        logged_in, fake_v1, capabilities, monkeypatch, caplog):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    fake_v1.replace(responses.GET, "", {
        **capabilities,
        "grant_types_supported": ["urn:ietf:params:oauth:grant-type:device_code"]})

    assert logged_in.open_url("http://portal.test/approve", "the page") is False

    assert opened == []
    assert "http://portal.test/approve" in caplog.text


def test_a_terms_refusal_names_each_document_its_own_way(logged_in, fake_v1, monkeypatch):
    '''🔴 Two documents with their own links, each printed beside its own; one
    with no link named by its title in `GET /v1/me`'s `terms`. Nothing is
    accepted; only an https link may be opened.'''
    opened = []
    monkeypatch.setattr(type(logged_in), "open_url",
                        lambda self, url, what, require_tty=True: opened.append(url))
    fake_v1.route(responses.POST, "jobs", problem("terms-not-accepted", 403, blocked_by={
        "tos": {"url": "https://portal.test/sign/tos"},
        "gf22-nda": {"url": "https://portal.test/sign/nda"},
        "export": {}}), status=403, content_type="application/problem+json")
    fake_v1.route(responses.GET, "me", {"id": "u1", "terms": [
        {"id": "export", "title": "Export Control Statement"}]})

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job(design="gcd", jobname="job0")

    text = str(raised.value)
    assert "sign tos: https://portal.test/sign/tos" in text
    assert "sign gf22-nda: https://portal.test/sign/nda" in text
    assert "sign Export Control Statement (no link" in text
    assert opened == ["https://portal.test/sign/tos", "https://portal.test/sign/nda"]
    assert not [c for c in fake_v1.calls if "accept" in c.request.url]


def test_a_blocked_artifact_names_each_document_its_own_way(fake_v1, logged_in):
    from siliconcompiler.remote.client.errors import blocked_lines

    lines = blocked_lines({"tos": {"url": "https://portal.test/sign/tos"},
                           "gf22-nda": {"url": "https://portal.test/sign/nda"},
                           "export": {}}, {"export": "Export Control Statement"})

    assert lines == ["sign tos: https://portal.test/sign/tos",
                     "sign gf22-nda: https://portal.test/sign/nda",
                     "sign Export Control Statement (no link is available; ask the "
                     "operator where)"]


def test_the_stream_url_is_never_printed(logged_in, fake_v1, monkeypatch, caplog):
    '''A storage or stream URL is a capability: never logged, printed or
    stored, error messages included.'''
    import logging

    from siliconcompiler.remote.client.logs import LogTail

    secret = f"{ORIGIN}/stream/logs/j1/place/0?expires=9&n=abc&sig=SECRET"
    fake_v1.route(responses.GET, "jobs/j1/logs", "", status=303,
                  headers={"Location": secret})
    fake_v1.elsewhere(responses.GET, f"{ORIGIN}/stream/logs/j1/place/0",
                      json.dumps(problem("limit-exceeded", 429)), status=429,
                      content_type="application/problem+json")
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ServerProblem) as raised:
        LogTail(logged_in, "j1", "place", "0").follow()

    assert "SECRET" not in str(raised.value) and "SECRET" not in caplog.text
