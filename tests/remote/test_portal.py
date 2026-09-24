import pytest

from conftest import call, login


pytest.importorskip("flask", reason="the server extra is not installed")


# The portal exists under one rule: every authorization decision goes through
# the code the API handlers call. A portal query that forgets `WHERE user_id =`
# answers 200 and looks correct, and this project has shipped that defect once.
# Most of what is asserted here is that the rule holds.


@pytest.fixture
def dispatcher(server):
    """Shared with the API's own tests, which is the point: the portal runs
    against the same server and the same fake cluster."""
    from test_server_jobs import FakeDispatcher

    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


@pytest.fixture
def signed_in(server, server_client, key, token):
    '''A browser that has been handed a session by the CLI.'''
    response = call(server_client, key, "POST", "/portal/session", token)
    assert response.status_code == 200

    url = response.get_json()["url"]
    entered = server_client.get(url.split("http://localhost", 1)[1])
    assert entered.status_code == 302
    return server_client


def csrf(client, path="/portal/"):
    page = client.get(path).get_data(as_text=True)
    marker = 'name="csrf" value="'
    return page.split(marker, 1)[1].split('"', 1)[0]


###########################
# Getting in
###########################

def test_a_browser_with_no_session_is_told_how_to_get_one(server_client):
    '''There is no identity provider here and a browser arriving cold holds
    none of what the CLI holds, so the answer is a command rather than a login
    form.'''
    response = server_client.get("/portal/")

    assert response.status_code == 401
    assert "sc-remote -portal" in response.get_data(as_text=True)


def test_the_handover_is_spent_on_arrival(server, server_client, key, token):
    '''🔴 The URL reaches the browser's history and possibly an access log.
    Spending it on arrival is what makes both worthless.'''
    url = call(server_client, key, "POST", "/portal/session",
               token).get_json()["url"]
    path = url.split("http://localhost", 1)[1]

    assert server_client.get(path).status_code == 302
    assert server_client.get(path).status_code == 403


def test_a_handover_link_that_was_never_minted(server_client):
    assert server_client.get("/portal/enter?token=invented").status_code == 403


def test_the_handover_needs_the_machine_key(server_client):
    '''It is the CLI proving possession of its registered key, so an
    unauthenticated caller gets nothing to open.'''
    assert server_client.post("/portal/session").status_code == 401


def test_a_portal_session_is_not_an_api_credential(signed_in):
    '''🔴 It mints no access token and carries no DPoP binding. A path from a
    cookie to an API credential would be the shortest way around the key
    pinning, so there is none.'''
    # The cookie is in the jar; the API still refuses.
    assert signed_in.get("/v1/jobs").status_code == 401
    assert signed_in.get("/v1/me").status_code == 401


def test_signing_out_ends_it(signed_in):
    signed_in.post("/portal/logout", data={"csrf": csrf(signed_in)})

    assert signed_in.get("/portal/").status_code == 401


###########################
# The screens
###########################

@pytest.mark.parametrize("path", ["/portal/", "/portal/devices",
                                  "/portal/account", "/portal/images"])
def test_every_screen_renders(signed_in, path):
    response = signed_in.get(path)

    assert response.status_code == 200
    assert "sc-server" in response.get_data(as_text=True)


def test_a_job_appears_on_the_jobs_screen(server_client, key, token,
                                          job_archive, dispatcher, signed_in):
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    page = signed_in.get("/portal/").get_data(as_text=True)

    assert "gcd" in page
    assert job["id"][:8] in page


def test_the_account_screen_says_the_identity_is_not_verified(signed_in):
    '''The honesty half, in the place a person reads rather than only in a
    startup log.'''
    page = signed_in.get("/portal/account").get_data(as_text=True)

    assert "does not verify who you are" in page
    assert "self-asserted" in page


def test_the_images_screen_says_what_registering_one_means(signed_in):
    '''🔴 The most dangerous write this server has, and the screen says so.'''
    page = signed_in.get("/portal/images").get_data(as_text=True)

    assert "chooses what code executes on the cluster" in page
    assert "declared and unverified" in page


###########################
# The rule the portal exists under
###########################

def test_a_stranger_cannot_read_another_persons_job(
        server, server_client, key, token, job_archive, dispatcher, signed_in):
    '''🔴 Through JobService.owned, which is the same predicate the API
    evaluates -- not a second query that could forget the WHERE.'''
    from siliconcompiler.remote import dpop
    from test_server_jobs import stage, submit

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    # A second person, with a portal session of their own.
    other_key = dpop.generate_key()
    other = login(server_client, other_key, subject="machine:2000").get_json()
    url = call(server_client, other_key, "POST", "/portal/session",
               other["access_token"]).get_json()["url"]
    server_client.get(url.split("http://localhost", 1)[1])

    assert server_client.get(f"/portal/jobs/{job['id']}").status_code == 404
    assert server_client.get(
        f"/portal/jobs/{job['id']}/artifacts").status_code == 404


def test_cancelling_from_the_browser_moves_the_job(
        server, server_client, key, token, job_archive, dispatcher, me,
        signed_in):
    '''The gate: a cancel in the browser is the cancel the CLI is waiting on.'''
    from test_server_jobs import running

    job = running(server, server_client, key, token, job_archive, me)

    signed_in.post(f"/portal/jobs/{job['id']}/cancel",
                   data={"csrf": csrf(signed_in), "reason": "from the portal"})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()
    assert read["state"] == "cancelling"
    assert dispatcher.cancelled == ["fake:1"]


def test_a_form_from_somewhere_else_is_refused(signed_in, server, server_client,
                                               key, token, job_archive,
                                               dispatcher, me):
    '''SameSite=Strict already refuses the cookie on a cross-site POST. This is
    the half that does not depend on the browser being recent.'''
    from test_server_jobs import running

    job = running(server, server_client, key, token, job_archive, me)

    response = signed_in.post(f"/portal/jobs/{job['id']}/cancel",
                              data={"csrf": "not-the-one"})

    assert response.status_code == 403
    assert not dispatcher.cancelled
