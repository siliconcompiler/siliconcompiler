import re

from urllib.parse import urlsplit

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import finish, proof, slug  # noqa: E402


def handover(server, send, **body):
    '''A fresh browser, and the answer to its sign-in request.'''
    return server.test_client(), send("POST", "/v1/auth/browser", json=body)


def path_of(answer):
    target = urlsplit(answer.get_json()["url"])
    return f"{target.path}?{target.query}"


def sign_in(server, send, **body):
    client, answer = handover(server, send, **body)
    client.get(path_of(answer))
    return client


def csrf(server, client):
    '''The token a page's forms carry, read from the session it belongs to.'''
    return server.config["SC_PORTAL"]._sessions[client.get_cookie("sc_portal").value][2]


def state(api, job):
    return api("GET", f"/v1/jobs/{job['id']}").get_json()["state"]


def test_the_handover_answers_a_single_use_url_and_lands_on_the_page(server, api, tree):
    job, _ = tree
    for body, landing in (({}, "/portal/"), ({"job_id": job["id"]}, f"/portal/jobs/{job['id']}")):
        client, answer = handover(server, api, **body)
        assert answer.status_code == 200
        assert answer.headers["Cache-Control"] == "private, no-store"
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", answer.get_json()["expires_at"])

        arrived = client.get(path_of(answer))
        assert (arrived.status_code, urlsplit(arrived.headers["Location"]).path) == (302, landing)
        assert "HttpOnly" in arrived.headers["Set-Cookie"]
        assert "SameSite=Lax" in arrived.headers["Set-Cookie"]
        assert client.get(landing).status_code == 200

        again = server.test_client().get(path_of(answer))
        assert (again.status_code, "Set-Cookie" in again.headers) == (403, False)


def test_an_expired_handover_is_refused(server, api):
    client, answer = handover(server, api)
    held = server.config["SC_PORTAL"]._handovers
    token, (user, _, landing) = next(iter(held.items()))
    held[token] = (user, 0, landing)

    assert client.get(path_of(answer)).status_code == 403
    assert client.get("/portal/").status_code == 401


def test_the_arrival_goes_only_where_the_token_was_minted_for(server, api):
    client, answer = handover(server, api)

    arrived = client.get(f"{path_of(answer)}&next=//evil.example/&return=https://evil.example")

    assert arrived.headers["Location"] == "/portal/"


@pytest.mark.parametrize("body, status, problem", [
    ({"job_id": "x", "terms_id": "y"}, 400, "invalid-request"),
    ({"other": "x"}, 400, "invalid-request"),
    ([], 400, "invalid-request"),
    ({"job_id": "no-such-job"}, 404, "not-found"),
    ({"terms_id": "tos"}, 404, "not-found"),
    ({"artifact_id": "a1"}, 404, "not-found"),
])
def test_a_handover_names_at_most_one_page_this_server_has(api, body, status, problem):
    refused = api("POST", "/v1/auth/browser", json=body)

    assert (refused.status_code, slug(refused)) == (status, problem)


def test_a_handover_for_a_strangers_job_is_not_found(stranger, tree):
    refused = stranger("POST", "/v1/auth/browser", json={"job_id": tree[0]["id"]})

    assert (refused.status_code, slug(refused)) == (404, "not-found")


def test_a_handover_needs_an_api_session(server_client):
    assert server_client.post("/v1/auth/browser", json={}).status_code == 401


def test_the_link_is_built_on_the_configured_origin_never_on_host(key):
    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.server.app import create_app

    origin = "https://sc.example"
    client = create_app("sc-server", public_origins=[origin]).test_client()
    token = client.post("/v1/auth/token", data={
        "grant_type": "client_credentials", "client_id": "local:x"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{origin}/v1/auth/token")}
    ).get_json()["access_token"]

    answer = client.post("/v1/auth/browser", json={}, base_url="https://evil.example", headers={
        "Authorization": f"DPoP {token}", "X-Forwarded-Host": "evil.example",
        "DPoP": dpop.sign_proof(key, "POST", f"{origin}/v1/auth/browser", access_token=token)})

    assert answer.get_json()["url"].startswith(f"{origin}/portal/enter?token=")


def test_the_portal_session_is_no_api_credential(server, api, key):
    browser = sign_in(server, api)
    cookie = browser.get_cookie("sc_portal").value

    assert browser.get("/v1/jobs").status_code == 401
    forged = browser.get("/v1/jobs", headers={
        "Authorization": f"DPoP {cookie}", "DPoP": proof(key, "GET", "/v1/jobs", cookie)})
    assert forged.status_code == 401


@pytest.mark.parametrize("method, path", [
    ("get", "/portal/"), ("get", "/portal/jobs/x"), ("post", "/portal/jobs/x/cancel"),
    ("post", "/portal/logout")])
def test_a_request_without_a_session_is_told_to_sign_in(server, method, path):
    refused = getattr(server.test_client(), method)(path)

    assert refused.status_code == 401
    assert "sc-config remote portal" in refused.text


def test_the_list_holds_only_the_callers_jobs(server, api, stranger, dispatcher, tree):
    job, _ = tree

    assert job["id"] in sign_in(server, api).get("/portal/").text
    assert job["id"] not in sign_in(server, stranger).get("/portal/").text


@pytest.mark.parametrize("action", ["cancel", "delete"])
def test_a_stranger_is_refused_a_job_page_and_its_actions(server, stranger, dispatcher, tree,
                                                          action):
    job, _ = tree
    other = sign_in(server, stranger)

    assert other.get(f"/portal/jobs/{job['id']}").status_code == 404
    refused = other.post(f"/portal/jobs/{job['id']}/{action}",
                         data={"csrf": csrf(server, other)})
    assert refused.status_code == 404


@pytest.mark.parametrize("action", ["cancel", "delete"])
@pytest.mark.parametrize("token", [None, "wrong"])
def test_an_action_without_the_sessions_csrf_token_is_refused(server, api, dispatcher, tree,
                                                              action, token):
    job, _ = tree
    finish(server, api, dispatcher, job)
    browser = sign_in(server, api)

    refused = browser.post(f"/portal/jobs/{job['id']}/{action}",
                           data={} if token is None else {"csrf": token})

    assert refused.status_code == 403
    assert state(api, job) == "completed"
    assert api("GET", f"/v1/jobs/{job['id']}").get_json()["deleted_at"] is None


def test_cancel_stops_a_running_job(server, api, dispatcher, tree):
    job, _ = tree
    browser = sign_in(server, api, job_id=job["id"])

    sent = browser.post(f"/portal/jobs/{job['id']}/cancel", data={"csrf": csrf(server, browser)})

    assert sent.status_code == 302
    assert state(api, job) in ("cancelling", "cancelled")
    assert dispatcher.cancelled


def test_delete_removes_a_finished_job_and_refuses_a_running_one(server, api, dispatcher, tree):
    job, _ = tree
    browser = sign_in(server, api)
    form = {"csrf": csrf(server, browser)}

    running = browser.post(f"/portal/jobs/{job['id']}/delete", data=form)
    assert running.status_code == 409

    finish(server, api, dispatcher, job)
    assert browser.post(f"/portal/jobs/{job['id']}/delete", data=form).status_code == 302
    assert job["id"] not in browser.get("/portal/").text
    assert browser.get(f"/portal/jobs/{job['id']}").status_code == 404


def test_a_finished_node_shows_its_log(server, api, dispatcher, tree):
    job, _ = tree
    finish(server, api, dispatcher, job)
    browser = sign_in(server, api, job_id=job["id"])

    page = browser.get(f"/portal/jobs/{job['id']}").text

    assert "stepone ran" in page and "steptwo ran" in page
    assert "completed" in page


def test_signing_out_ends_the_session(server, api):
    browser = sign_in(server, api)

    assert browser.post("/portal/logout", data={"csrf": csrf(server, browser)}).status_code == 200
    assert browser.get("/portal/").status_code == 401
