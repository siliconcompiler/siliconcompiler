import json
import logging

import pytest
import responses

from conftest import asked_for_pages, problem, refused

from siliconcompiler.remote import ServerProblem
from siliconcompiler.remote.client import OAuthRefusal, cli
from siliconcompiler.remote.client.errors import REGISTERED, clean, describe


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
    assert "not an https URL" in caplog.text
    assert "portal.test" not in caplog.text


def test_a_single_use_sign_in_url_is_printed_where_no_browser_opened_and_never_logged(
        logged_in, fake_v1, capabilities, monkeypatch, capsys, caplog):
    '''Not opened as it is not https, so the warning names no URL and the terminal
    gets it once.'''
    url = "http://portal.test/enter?token=single-use-secret"
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda target: opened.append(target) or True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    fake_v1.replace(responses.GET, "", {**capabilities, "grant_types_supported": [
        "urn:ietf:params:oauth:grant-type:device_code"]})

    assert logged_in._show({"url": url, "expires_at": "2026-10-01T18:04:30Z"},
                           "the page") is False

    assert opened == []
    assert "single-use-secret" not in caplog.text
    assert capsys.readouterr().out.count(url) == 1


def test_the_clients_registry_is_the_error_pages_the_deployment_serves():
    '''A `type` outside what the client knows is acted on as an untyped failure, so a
    slug missing here would be waited out wrongly and one extra would be trusted.'''
    from pathlib import Path

    import siliconcompiler.remote as remote

    pages = Path(remote.__file__).parent / "server" / "errorpages"
    served = {page.stem for page in pages.glob("*.html")
              if not page.name.startswith("_") and page.stem != "index"}

    assert REGISTERED == served
    assert ServerProblem(problem("rate-limited", 429), 429).slug == "rate-limited"
    assert ServerProblem(problem("brand-new-limit", 429), 429).slug is None


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


def test_a_presigned_url_is_not_logged_by_the_http_library_at_debug(caplog):
    '''urllib3's request line carries the path and query, a signature included;
    its other lines are kept.'''
    pool = logging.getLogger("urllib3.connectionpool")
    caplog.set_level(logging.DEBUG)

    pool.debug('%s://%s:%s "%s %s %s" %s %s', "https", "storage.test", 443, "PUT",
               "/obj?X-Amz-Signature=secret", "HTTP/1.1", 200, 0)
    pool.debug("Starting new HTTPS connection (%d): %s:%s", 1, "storage.test", 443)
    pool.warning("Retrying (Retry(total=2)) after connection broken")

    assert "X-Amz-Signature" not in caplog.text
    assert "Starting new HTTPS connection" in caplog.text
    assert "Retrying" in caplog.text


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
