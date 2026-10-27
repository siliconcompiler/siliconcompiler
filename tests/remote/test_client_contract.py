import json
import logging

import pytest
import responses

from conftest import asked_for_pages, problem, refused

from siliconcompiler.remote import ServerProblem
from siliconcompiler.remote.client import OAuthRefusal, cli
from siliconcompiler.remote.client.errors import clean, describe


# The client half of the v1 API's behaviour tests that the rest of the suite
# does not already hold.

ORIGIN = "https://sc-server.test"


def test_an_unknown_response_member_is_ignored(logged_in, fake_v1, capabilities,
                                               nop_project, monkeypatch):
    from siliconcompiler.remote.client.run import RemoteRun

    monkeypatch.setattr("siliconcompiler.remote.client.run.time.sleep", lambda s: None)
    fake_v1.replace(responses.GET, "",
                    dict(capabilities, a_member_from_later={"anything": [1, 2]}))
    fake_v1.route(responses.GET, "jobs/j1", {
        "id": "j1", "state": "completed", "terminal": True, "nodes": [],
        "progress": {"total_count": 0, "completed_count": 0, "failed_count": 0},
        "a_member_from_later": {"x": 1}})

    assert logged_in.capabilities()["api_version"] == "v1"
    RemoteRun(nop_project, logged_in)._poll("j1")


@pytest.mark.parametrize("path,body", [
    ("auth/token", {"error": "invalid_grant", "reason": "reused"}),
    ("auth/device", {"error": "invalid_client", "error_description": "bound to a key"}),
])
def test_an_oauth_error_is_read_for_error_and_reason(fake_v1, logged_in, path, body):
    '''The OAuth shape: `error`, then `reason` where there is one, never `type`.'''
    fake_v1.route(responses.POST, path, body, status=400)

    with pytest.raises(OAuthRefusal) as raised:
        logged_in.transport.request("POST", path, data={"grant_type": "x"},
                                    authenticated=False, oauth=True)

    assert (raised.value.error, raised.value.reason) == (body["error"], body.get("reason"))


def test_server_text_loses_its_control_characters_and_keeps_its_colour():
    text = clean("bad\x00 bell\x07 clear\x1b[2J red\x1b[31mX\x1b[0m\ttab")

    assert "\x00" not in text and "\x07" not in text and "\x1b[2J" not in text
    assert "\x1b[31mX\x1b[0m" in text and "\ttab" in text


def test_the_deployment_notice_and_refusal_lines_lose_control_characters(
        logged_in, fake_v1, capabilities, caplog):
    evil = "\x1b]0;owned\x07"
    fake_v1.replace(responses.GET, "", dict(
        capabilities, api_version=f"v1{evil}", identity_assurance=evil,
        grant_types_supported=[evil], features=[evil], limits={evil: 1},
        software={"python": {evil: [evil]}, "tools": {}}, terms_url=evil,
        notices=[{"level": "info", "message": f"down{evil} soon", "starts_at": None,
                  "ends_at": None}]))
    fake_v1.route(responses.GET, "healthz", {"status": evil})
    caplog.set_level(logging.INFO)

    logged_in.capabilities()
    cli.print_deployment(logged_in)
    logged_in._report_software({"software": {"python": {"siliconcompiler": [evil]}}})
    rendered = [describe(problem("not-found", 404, trace_id=evil), help_url=evil),
                describe(dict(problem("not-found", 404), type=evil), job_id=evil)]

    for text in (caplog.text, *rendered):
        assert "\x07" not in text and "\x1b]" not in text


@pytest.mark.parametrize("offered", [
    ["urn:ietf:params:oauth:grant-type:device_code"],
    ["client_credentials", "urn:ietf:params:oauth:grant-type:device_code"],
], ids=["device-grant", "and-client-credentials"])
def test_an_http_url_from_a_deployment_that_authenticates_is_printed_not_opened(
        logged_in, fake_v1, capabilities, monkeypatch, caplog, offered):
    '''Offering `client_credentials` beside a grant that authenticates is still a
    deployment that authenticates.'''
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    fake_v1.replace(responses.GET, "", {**capabilities, "grant_types_supported": offered})

    assert logged_in.open_url("http://portal.test/approve", "the page") is False

    assert opened == []
    assert "http://portal.test/approve" in caplog.text


def terms_refusal(fake_v1):
    refused(fake_v1, responses.POST, "jobs", "terms-not-accepted", 403,
            blocked_by=["tos", "gf22-nda", "export"])
    fake_v1.route(responses.GET, "me", {"id": "u1", "terms": [
        {"id": "tos", "title": "Terms of Service", "can_decide": True},
        {"id": "export", "title": "Export Control Statement", "can_decide": True}]})
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://portal.test/enter?token=t1",
                   "expires_at": "2026-10-01T18:04:30Z"})


@pytest.mark.parametrize("tty", [True, False], ids=["terminal", "no-terminal"])
def test_a_terms_refusal_names_each_document_and_opens_its_page(logged_in, fake_v1,
                                                                monkeypatch, tty):
    '''`blocked_by` is `terms` ids, named by title from
    `GET /v1/me`, else by id; on a terminal each page is asked for at
    endpoint 6 and opened, off one none is minted. Nothing is accepted.'''
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: tty)
    monkeypatch.delenv("CI", raising=False)
    terms_refusal(fake_v1)

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job(design="gcd", jobname="job0")

    text = str(raised.value)
    assert "sign Terms of Service" in text
    assert "sign gf22-nda" in text
    assert "sign Export Control Statement" in text
    assert "portal.test" not in text
    if tty:
        assert asked_for_pages(fake_v1) == [{"terms_id": "tos"}, {"terms_id": "gf22-nda"},
                                            {"terms_id": "export"}]
        assert opened == ["https://portal.test/enter?token=t1"] * 3
    else:
        assert asked_for_pages(fake_v1) == [] and opened == []
    assert not [c for c in fake_v1.calls if "accept" in c.request.url]


def test_the_stream_url_is_never_printed(logged_in, fake_v1, caplog):
    '''A storage or stream URL is a capability: never logged or printed,
    error messages included.'''
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
