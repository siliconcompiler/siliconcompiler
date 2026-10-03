import json
import uuid

import pytest

from conftest import call, login, slug
from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import OAuthError
from siliconcompiler.remote.server.identity.auth import SCOPES, expand_scope


pytest.importorskip("flask", reason="the server extra is not installed")


BASE = "http://localhost/v1"
CC = {"grant_type": "client_credentials", "client_id": "local:machine:1000"}


@pytest.fixture
def client(server_client):
    return server_client


def oauth(response):
    '''The OAuth shape: `error`, and never a problem+json `type`.'''
    body = response.get_json()
    assert "type" not in body, body
    assert response.mimetype == "application/json"
    return body["error"], body.get("reason")


def form_post(client, key, form, path="/v1/auth/token"):
    '''A form POST to an OAuth endpoint, proved by ``key`` where there is one.'''
    headers = {"DPoP": dpop.sign_proof(key, "POST", f"http://localhost{path}")} if key else {}
    return client.post(path, data=form, headers=headers,
                       content_type="application/x-www-form-urlencoded")


def refreshing(client, token, signer, **extra):
    return form_post(client, signer,
                     {"grant_type": "refresh_token", "refresh_token": token, **extra})


def test_the_vocabulary_is_the_registered_scopes():
    '''Every one <resource>:<action>, none administrative; omitting scope asks
    for all of them.'''
    assert set(SCOPES) == {"jobs:read", "jobs:write", "jobs:delete", "artifacts:read",
                           "devices:read", "devices:write", "profile:read"}
    assert all(s.count(":") == 1 for s in SCOPES)
    assert set(expand_scope(None).split()) == set(SCOPES)


@pytest.mark.parametrize("asked,granted", [
    ("jobs:write", "jobs:read jobs:write"),                  # write carries read
    ("jobs:delete", "jobs:read jobs:delete"),
    ("devices:write", "devices:read devices:write"),
    ("jobs:read nosuch:thing", "jobs:read"),                  # the unknown dropped
    # Stable, so a client can compare two tokens' strings.
    ("profile:read jobs:read", "jobs:read profile:read"),
    ("jobs:read profile:read", "jobs:read profile:read"),
])
def test_a_scope_expands_to_what_is_granted(asked, granted):
    assert expand_scope(asked) == granted


def test_nothing_recognised_left_is_invalid_scope():
    with pytest.raises(OAuthError) as raised:
        expand_scope("nosuch:thing admin:all")

    assert raised.value.error == "invalid_scope"


def test_a_session_with_no_human_involved(client, key, server):
    '''`no-store` is RFC 6749's MUST on tokens; `scope` is always sent (stricter
    than RFC 6749) and says what was granted; an unknown parameter is ignored
    (§3.2). First contact records the key.'''
    response = login(client, key, some_future_parameter="x")

    assert response.status_code == 200
    body = response.get_json()
    assert body["token_type"] == "DPoP"      # never Bearer
    assert body["expires_in"] == 900
    assert body["refresh_token"]
    assert set(body["scope"].split()) == set(SCOPES)
    assert response.headers["Cache-Control"] == "no-store"
    store = server.config["SC_STORE"]
    assert store.one("SELECT * FROM devices")["dpop_jkt"] == \
        dpop.jwk_thumbprint(dpop.public_jwk(key))
    assert store.one("SELECT kind FROM device_events")["kind"] == "enrolled"

    narrowed = login(client, key, scope="jobs:read nosuch:thing")
    assert (narrowed.status_code, narrowed.get_json()["scope"]) == (200, "jobs:read")


def test_the_token_endpoint_needs_a_proof(client):
    response = form_post(client, None, {"grant_type": "client_credentials"})

    assert response.status_code == 400
    assert oauth(response) == ("invalid_dpop_proof", None)


@pytest.mark.parametrize("path,form,error", [
    ("/v1/auth/token", {"grant_type": "password"}, "unsupported_grant_type"),
    ("/v1/auth/token", {"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": "whatever"}, "unsupported_grant_type"),
    ("/v1/auth/token", {"grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                        "device_code": "whatever"}, "unsupported_grant_type"),
    # Routed and refused, not unrouted: the login's cue to use client_credentials.
    ("/v1/auth/device", {"scope": " ".join(SCOPES)}, "unsupported_grant_type"),
    ("/v1/auth/token", {"grant_type": "client_credentials", "client_id": "nope"},
     "invalid_request"),
    # The three that would be misunderstood.
    ("/v1/auth/token", dict(CC, actor_token="x"), "invalid_request"),
    ("/v1/auth/token", dict(CC, audience="x"), "invalid_request"),
    ("/v1/auth/token", dict(CC, resource="x"), "invalid_request"),
    ("/v1/auth/token", dict(CC, machine_id_source="dmi_uuid"), "invalid_request"),
    ("/v1/auth/token", dict(CC, scope="nosuch:thing"), "invalid_scope"),
], ids=["password", "device-code", "token-exchange", "device-endpoint", "client-id",
        "actor-token", "audience", "resource", "machine-id-source", "scope"])
def test_an_oauth_refusal_is_a_400_in_the_oauth_shape(client, key, path, form, error):
    response = form_post(client, key, form, path)

    assert response.status_code == 400
    assert oauth(response) == (error, None)


def test_the_token_endpoint_is_form_encoded(client, key):
    '''A 415 is raised before any OAuth processing, so it is problem+json.'''
    response = client.post(
        "/v1/auth/token", json={"grant_type": "client_credentials"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")})

    assert response.status_code == 415
    assert slug(response) == "unsupported-media-type"
    assert response.mimetype == "application/problem+json"
    assert "error" not in response.get_json()


@pytest.mark.parametrize("path", ["/v1/auth/token", "/v1/auth/device"])
def test_a_method_refusal_at_an_oauth_endpoint_is_problem_json(client, path):
    response = client.get(path)

    assert response.status_code == 405
    assert slug(response) == "method-not-allowed"
    assert "error" not in response.get_json()


@pytest.mark.parametrize("address", ["127.0.0.1", "::1"])
def test_one_user_cannot_claim_another(client, key, server, address):
    '''Without the binding, A on a shared machine presents B's public
    derivation with A's own key and becomes B. Never rebound automatically,
    loopback included (profile §7): `invalid_client`, saying why, recorded.'''
    client.environ_base["REMOTE_ADDR"] = address
    login(client, key, subject="machine:1001")

    response = login(client, dpop.generate_key(), subject="machine:1001")

    assert response.status_code == 401
    assert oauth(response) == ("invalid_client", None)
    assert "bound to a different key" in response.get_json()["error_description"]
    assert "reauth_failed" in [row["kind"] for row in
                               server.config["SC_STORE"].all("SELECT kind FROM device_events")]


def test_the_operator_can_release_a_binding(client, key, server):
    '''The recovery path is a person: the registry CLI's release-binding.'''
    from siliconcompiler.remote.server.software import registry

    login(client, key, subject="machine:1001")
    replacement = dpop.generate_key()
    assert login(client, replacement, subject="machine:1001").status_code == 401

    assert registry.main(["-datadir", str(server.config["SC_DATADIR"]),
                          "release-binding", "machine:1001"]) == 0

    assert login(client, replacement, subject="machine:1001").status_code == 200


def test_binding_can_be_turned_off_for_a_container_fleet():
    '''/etc/machine-id is per image, so every container derives one subject;
    turning binding off declares a single trust domain.'''
    from siliconcompiler.remote.server.app import create_app

    client = create_app("datadir", bind_keys=False).test_client()

    login(client, dpop.generate_key(), subject="image:1000")
    assert login(client, dpop.generate_key(), subject="image:1000").status_code == 200


def test_two_subjects_are_two_identities(client):
    '''A machine-only key would make every user on a login node one identity.
    Another's device is a 404, not a 403 confirming the id is somebody's.'''
    alice, bob = dpop.generate_key(), dpop.generate_key()
    a = login(client, alice, subject="machine:1000").get_json()["access_token"]
    b = login(client, bob, subject="machine:1001").get_json()["access_token"]

    assert call(client, alice, "GET", "/v1/me", a).get_json()["id"] != \
        call(client, bob, "GET", "/v1/me", b).get_json()["id"]

    hers = call(client, alice, "GET", "/v1/devices", a).get_json()["items"][0]["id"]
    response = call(client, bob, "GET", f"/v1/devices/{hers}", b)
    assert (response.status_code, slug(response)) == (404, "not-found")


def test_a_changed_derivation_with_the_same_key_is_a_new_identity(server, client, key):
    '''A reimaged host, rebuilt container, changed uid or moved salt presents
    the SAME key under a NEW subject; it used to 500 on the unique thumbprint.
    A new identity, seeing none of the old one's jobs; the old enrolment ends
    (`session-ended`: re-authenticate, do NOT refresh), and is recorded.'''
    first = login(client, key, subject="machine-old:1000")
    assert first.status_code == 200
    old = first.get_json()["access_token"]
    was = call(client, key, "GET", "/v1/me", old).get_json()["id"]
    call(client, key, "POST", "/v1/jobs", old, json={"design": "gcd", "jobname": "job0"})

    second = login(client, key, subject="machine-new:1000")
    assert second.status_code == 200
    new = second.get_json()["access_token"]

    assert call(client, key, "GET", "/v1/me", new).get_json()["id"] != was
    assert call(client, key, "GET", "/v1/jobs", new).get_json()["items"] == []
    stale = call(client, key, "GET", "/v1/me", old)
    assert (stale.status_code, slug(stale)) == (401, "session-ended")
    assert [row["kind"] for row in server.config["SC_STORE"].all(
        "SELECT kind FROM device_events ORDER BY id")] == ["enrolled", "revoked", "enrolled"]


def test_a_token_needs_a_fresh_proof_by_its_own_key(client, key):
    '''The point of DPoP: a stolen token proves nothing alone, and one proof
    is one request.'''
    token = login(client, key).get_json()["access_token"]
    headers = {"Authorization": f"DPoP {token}",
               "DPoP": dpop.sign_proof(key, "GET", f"{BASE}/me", access_token=token)}
    assert client.get("/v1/me", headers=headers).status_code == 200

    for refused in (call(client, dpop.generate_key(), "GET", "/v1/me", token),
                    client.get("/v1/me", headers={"Authorization": f"DPoP {token}"}),
                    client.get("/v1/me", headers=headers)):          # replayed
        assert (refused.status_code, slug(refused)) == (401, "invalid-dpop-proof")


def test_no_credential_carries_a_challenge(client):
    response = client.get("/v1/me")

    assert (response.status_code, slug(response)) == (401, "invalid-token")
    assert response.headers["WWW-Authenticate"].startswith("DPoP")


def test_one_proof_sent_twice_at_once_is_taken_once(server, key):
    '''Two requests on two threads with one proof must not both read it as
    unseen; the check is widened so they always overlap.'''
    import threading
    import time

    issuer = server.config["SC_ISSUER"]

    class Slow(dict):
        def __contains__(self, item):
            found = dict.__contains__(self, item)
            time.sleep(0.2)
            return found

    issuer._seen = Slow()
    proof = dpop.sign_proof(key, "GET", f"{BASE}/me")
    outcomes = []

    def check():
        try:
            issuer._check_replay(proof)
            outcomes.append("taken")
        except Exception as e:                                   # noqa: BLE001
            outcomes.append(type(e).__name__)

    both = [threading.Thread(target=check) for _ in range(2)]
    for thread in both:
        thread.start()
    for thread in both:
        thread.join()

    assert sorted(outcomes) == ["ProblemError", "taken"]


def test_insufficient_scope_names_the_scope_needed(client, key):
    '''A refresh re-mints the same ceiling, so the client fails rather than loop.'''
    token = login(client, key, scope="jobs:read").get_json()["access_token"]

    response = call(client, key, "GET", "/v1/me", token)

    assert (response.status_code, slug(response)) == (403, "insufficient-scope")
    assert 'scope="profile:read"' in response.headers["WWW-Authenticate"]


@pytest.mark.parametrize("signed", ["http://LOCALHOST/v1/me", "http://localhost:80/v1/me",
                                    "HTTP://Localhost:80/v1/me"])
def test_a_proof_signed_for_a_canonical_equivalent_is_accepted(server_client, key, token,
                                                               signed):
    '''Identity *The proof rules*: `htu` and the configured origin are
    compared canonical, so `:80` or a mixed-case host is accepted.'''
    from test_dpop import proof_with_htu

    response = server_client.get("/v1/me", headers={
        "Authorization": f"DPoP {token}",
        "DPoP": proof_with_htu(key, "GET", signed, access_token=token)})

    assert response.status_code == 200, response.get_json()


def test_a_refresh_rotates_and_a_lost_response_gets_the_same_pair(client, key, server):
    '''A client whose response was lost retries a token already rotated:
    the replacement already issued, never a second live refresh token.'''
    first = login(client, key).get_json()

    one = refreshing(client, first["refresh_token"], key)
    two = refreshing(client, first["refresh_token"], key)

    assert one.status_code == two.status_code == 200
    assert one.get_json()["refresh_token"] != first["refresh_token"]
    assert one.get_json()["refresh_token"] == two.get_json()["refresh_token"]
    assert len(server.config["SC_STORE"].all(
        "SELECT jti FROM refresh_tokens WHERE replaced_at IS NULL")) == 1


def test_a_refresh_returns_the_full_scope_whatever_it_asks(client, key, server):
    '''Rule 3: a refresh never narrows a session, nor writes a narrowed scope.'''
    first = login(client, key, scope="jobs:write profile:read").get_json()
    assert first["scope"] == "jobs:read jobs:write profile:read"

    again = refreshing(client, first["refresh_token"], key, scope="jobs:read").get_json()

    assert again["scope"] == "jobs:read jobs:write profile:read"
    assert server.config["SC_STORE"].one("SELECT scope FROM token_families")["scope"] == \
        "jobs:read jobs:write profile:read"


def test_a_repeat_after_the_window_ends_the_session_as_reused(client, key, server):
    '''The whole family dies; the window is 300 s, this deployment's "a few
    minutes" (profile §6).'''
    from siliconcompiler.remote.server.identity import auth

    first = login(client, key).get_json()
    second = refreshing(client, first["refresh_token"], key).get_json()
    server.config["SC_STORE"].execute(
        "UPDATE refresh_tokens SET replaced_at = '2020-01-01T00:00:00.000Z' "
        "WHERE replaced_at IS NOT NULL")

    assert auth.REFRESH_GRACE_SECONDS == 300
    response = refreshing(client, first["refresh_token"], key)

    assert response.status_code == 400
    assert oauth(response) == ("invalid_grant", "reused")
    assert oauth(refreshing(client, second["refresh_token"], key)) == \
        ("invalid_grant", "reused")
    assert server.config["SC_STORE"].one(
        "SELECT revoked_reason FROM token_families")["revoked_reason"] == "reuse_detected"


def test_a_dead_refresh_token_is_invalid_grant_with_its_reason(client, key):
    first = login(client, key).get_json()
    assert oauth(refreshing(client, "not-a-token", key)) == ("invalid_grant", None)

    call(client, key, "POST", "/v1/auth/revoke", first["access_token"])

    assert oauth(refreshing(client, first["refresh_token"], key)) == ("invalid_grant", "revoked")


def test_a_changed_fingerprint_steps_up_and_revokes_nothing(client, key, server):
    '''Identity §6: a wrong fingerprint with a valid key is a machine that
    changed: `invalid_grant` with no reason, and the session lives.'''
    first = login(client, key, machine_id_hash="aaaa",
                  machine_id_source="linux_machine_id").get_json()

    moved = refreshing(client, first["refresh_token"], key, machine_id_hash="bbbb",
                       machine_id_source="linux_machine_id")

    assert moved.status_code == 400
    assert oauth(moved) == ("invalid_grant", None)
    assert server.config["SC_STORE"].one(
        "SELECT revoked_at FROM token_families")["revoked_at"] is None
    assert refreshing(client, first["refresh_token"], key, machine_id_hash="aaaa",
                      machine_id_source="linux_machine_id").status_code == 200


def test_a_device_enrolled_with_none_has_no_change_detection(client, key):
    first = login(client, key).get_json()

    assert refreshing(client, first["refresh_token"], key, machine_id_hash="cccc",
                      machine_id_source="linux_machine_id").status_code == 200


def test_a_refresh_is_bound_to_the_key_and_a_foreign_proof_revokes_nothing(client, key):
    '''Identity D56: reuse is judged only after the proof verifies, or a
    leaked, long-rotated token could end the owner's session without the key.'''
    first = login(client, key).get_json()["refresh_token"]
    second = refreshing(client, first, key).get_json()["refresh_token"]
    third = refreshing(client, second, key).get_json()["refresh_token"]

    for token in (first, third):
        stolen = refreshing(client, token, dpop.generate_key())
        assert stolen.status_code == 400
        assert oauth(stolen) == ("invalid_dpop_proof", None)
    assert refreshing(client, third, key).status_code == 200


def test_a_refresh_counts_as_the_device_being_seen(client, key):
    '''A rotation is the only signal most devices give: written only at
    `client_credentials`, `last_seen_at` stayed NULL all day.'''
    granted = login(client, key).get_json()

    def seen(token):
        return call(client, key, "GET", "/v1/devices", token).get_json()["items"][0][
            "last_seen_at"]

    first = seen(granted["access_token"])
    assert first is not None

    rotated = refreshing(client, granted["refresh_token"], key).get_json()

    assert seen(rotated["access_token"]) >= first


def test_a_revoked_session_says_so_in_the_wire_vocabulary(client, key, server):
    '''Revoking needs no scope: a logout that can be scoped away is a session
    nobody can close. Three stored reasons, one client branch; the column
    keeps why.'''
    token = login(client, key, scope="jobs:read").get_json()["access_token"]
    assert call(client, key, "POST", "/v1/auth/revoke", token).status_code == 204

    response = call(client, key, "GET", "/v1/me", token)

    assert (response.status_code, slug(response)) == (401, "session-ended")
    assert response.get_json()["reason"] in ("revoked", "deactivated", "expired")
    assert server.config["SC_STORE"].one(
        "SELECT revoked_reason FROM token_families")["revoked_reason"] == "user_logout"


def test_a_session_ends_for_the_registrys_reasons_and_no_other():
    '''A closed set, each cause mapped onto one: all re-authenticate.'''
    from siliconcompiler.remote.server.identity import auth

    reasons = ("revoked", "reused", "deactivated", "expired")
    assert set(auth._ENDED) == set(reasons)
    assert set(auth._WIRE_REASON.values()) <= set(reasons)


def test_revoking_a_device_ends_its_sessions(client, key):
    token = login(client, key).get_json()["access_token"]
    device = call(client, key, "GET", "/v1/devices", token).get_json()["items"][0]

    assert call(client, key, "DELETE", f"/v1/devices/{device['id']}",
                token).status_code == 204
    assert call(client, key, "GET", "/v1/me", token).status_code == 401


def proxied(tmp_path, *origins):
    from siliconcompiler.remote.server.app import create_app

    datadir = tmp_path / "proxied"
    datadir.mkdir()
    (datadir / "config.json").write_text(json.dumps({"public_origins": list(origins)}))
    return create_app(datadir).test_client()


def via(client, key, origin, method, path, token=None, host="backend:8080", **kwargs):
    '''A request signed for ``origin``, arriving as a proxy forwards it: plain
    http, to the backend's Host.'''
    headers = {"Host": host,
               "DPoP": dpop.sign_proof(key, method, origin + path, access_token=token)}
    if token:
        headers["Authorization"] = f"DPoP {token}"
    return client.open(path, method=method, headers=headers, **kwargs)


def proxied_token(client, key, origin, host="backend:8080"):
    return via(client, key, origin, "POST", "/v1/auth/token", host=host, data=CC,
               content_type="application/x-www-form-urlencoded").get_json()["access_token"]


@pytest.mark.parametrize("signed", ["https://sc.example.test", "http://lab.test:8080"])
def test_the_scheme_a_request_arrived_on_is_its_htus_origin(tmp_path, signed):
    '''Contract rule 5 (D70): the configured origin the proof's `htu`
    matched -- never the socket's, which behind a TLS-terminating proxy is
    http whichever origin the client used.'''
    client = proxied(tmp_path, "http://lab.test:8080", "https://sc.example.test")
    key = dpop.generate_key()
    token = proxied_token(client, key, signed, host="lab.test:8080")

    page = via(client, key, signed, "POST", "/v1/auth/browser", token, host="lab.test:8080",
               json={}).get_json()

    assert page["url"].startswith(f"{signed}/portal/enter?token=")


def test_htu_and_handed_out_urls_come_from_config_behind_a_proxy(tmp_path):
    '''A proxy rewrites `Host`: proofs are checked against, and every URL is
    built on, the configured origin -- the grant, the sign-in link, the logs'
    `303`s -- never the header.'''
    public = "https://sc.example.test"
    client = proxied(tmp_path, public)
    key = dpop.generate_key()
    token = proxied_token(client, key, public)

    def authed(method, path, **kwargs):
        return via(client, key, public, method, path, token, **kwargs)

    job = authed("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    grant = authed("POST", f"/v1/jobs/{job['id']}/upload-grant",
                   json={"size_bytes": 10, "digest": "sha256:" + "0" * 64}).get_json()
    assert grant["url"].startswith(f"{public}/storage/upload/")
    assert authed("POST", "/v1/auth/browser", json={}).get_json()["url"] \
        .startswith(f"{public}/portal/")

    store = client.application.config["SC_STORE"]
    running = str(uuid.uuid4())
    store.execute("INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
                  "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job1', '{}', 'none')",
                  (running, authed("GET", "/v1/me").get_json()["id"]))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (running,))
    node = authed("GET", f"/v1/jobs/{running}/logs?step=place&index=0")
    assert node.status_code == 303, node.get_json()
    assert node.headers["Location"].startswith(f"{public}/stream/logs/{running}/place/0?")
    assert authed("GET", f"/v1/jobs/{running}/logs").headers["Location"] \
        .startswith(f"{public}/stream/logs/{running}?")

    # A proof made for the Host the proxy wrote is not a proof for this server.
    wrong = via(client, key, "http://backend:8080", "GET", "/v1/me", token)
    assert (wrong.status_code, slug(wrong)) == (401, "invalid-dpop-proof")


def test_me_reports_the_callers_account(client, key):
    '''`authorized` is omitted, since {} would claim "granted nothing" where
    there are no grants; `projects` is sent empty, deliberately. `limits`
    are the caller's effective values: `GET /v1` takes no credential, so cannot
    vary by caller. `usage` is derived, never metered: `used` this calendar
    month, `total` everything, `null` on a stock (entitlements §3; D74).'''
    token = login(client, key).get_json()["access_token"]
    body = call(client, key, "GET", "/v1/me", token).get_json()

    assert "authorized" not in body and "blocked_type" not in body
    assert (body["projects"], body["terms"], body["can_submit"]) == ([], [], True)

    assert set(body["limits"]) == {"concurrent_jobs", "concurrent_nodes",
                                   "pending_uploads", "max_job_nodes", "devices",
                                   "artifact_retention_seconds", "max_download_bytes",
                                   "max_staging_seconds"}
    assert body["limits"]["artifact_retention_seconds"] == 2592000
    assert body["limits"]["max_staging_seconds"] == 3600

    usage = body["usage"]
    assert set(usage) == {"compute_seconds", "license_seconds", "storage_bytes",
                          "concurrent_jobs"}
    assert usage["concurrent_jobs"] == 0
    assert usage["license_seconds"] == {}             # no license is metered here
    compute, storage = usage["compute_seconds"], usage["storage_bytes"]
    for member in ("used", "total", "limit", "window", "resets_at"):
        assert member in compute and member in storage, member
    assert (compute["limit"], compute["total"]) == (None, 0)
    assert compute["resets_at"].endswith("Z")         # calendar windows: a real instant
    assert (storage["total"], storage["window"], storage["resets_at"]) == (None, None, None)


def test_me_carries_the_session_the_request_was_made_in(client, key):
    '''From the calling token's family and device, every member REQUIRED
    (surface §5; D276), and reading it rotates nothing.'''
    first = login(client, key).get_json()
    session = call(client, key, "GET", "/v1/me", first["access_token"]).get_json()["session"]

    assert session["kind"] == "interactive"
    assert session["scope"] == first["scope"]
    assert session["device_id"] == call(client, key, "GET", "/v1/devices",
                                        first["access_token"]).get_json()["items"][0]["id"]
    for member in ("access_expires_at", "refresh_expires_at", "session_expires_at"):
        assert session[member].endswith("Z"), member
    assert session["refresh_expires_at"] <= session["session_expires_at"]

    assert refreshing(client, first["refresh_token"], key).status_code == 200


def test_a_ci_session_has_no_device_and_no_refresh(server):
    '''`device_id` and `refresh_expires_at` null. CI credentials are
    crucible's, so the family is written as crucible writes one.'''
    from siliconcompiler.remote.server.identity import accounts
    from siliconcompiler.remote.server.identity.auth import Session

    store = server.config["SC_STORE"]
    user = store.upsert_user("ci", "pipeline")
    store.execute(
        "INSERT INTO token_families (id, user_id, device_id, kind, dpop_jkt, scope, "
        "  expires_at) VALUES ('fam-ci', ?, NULL, 'ci', 'jkt', "
        "  'jobs:read jobs:write', '2026-12-01T00:00:00.000Z')", (user["id"],))

    view = accounts.session_view(store, Session(
        user_id=user["id"], scope="jobs:read jobs:write", family_id="fam-ci",
        device_id=None, jkt="jkt", expires_at=1790000000))

    assert (view["kind"], view["device_id"], view["refresh_expires_at"]) == ("ci", None, None)
    assert view["scope"] == "jobs:read jobs:write"
    assert view["session_expires_at"] == "2026-12-01T00:00:00.000Z"


def test_authenticated_responses_are_never_cacheable(client, key):
    '''A cache rule matching /v1/* would serve one caller's response to another.'''
    token = login(client, key).get_json()["access_token"]

    for path in ("/v1/me", "/v1/devices"):
        assert call(client, key, "GET", path, token).headers["Cache-Control"] == \
            "private, no-store"


def test_a_per_account_download_ceiling(client, key):
    '''An override reaches the caller on `/v1/me`, never `GET /v1`. The
    table stores unlimited as `-1` (the wire spent `null` on it, and the table
    needs `null` for *inherit*); only a declared limit can be overridden.'''
    from siliconcompiler.remote.server.identity import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()
    store = client.application.config["SC_STORE"]
    default = client.get("/v1").get_json()["limits"]["max_download_bytes"]

    def mine():
        return call(client, key, "GET", "/v1/me", token).get_json()["limits"][
            "max_download_bytes"]

    assert me["limits"]["max_download_bytes"] == default
    accounts.set_limit(store, me["id"], "max_download_bytes", 1024, me["id"],
                       note="a slow link")
    assert mine() == 1024
    assert client.get("/v1").get_json()["limits"]["max_download_bytes"] == default

    accounts.set_limit(store, me["id"], "max_download_bytes", -1, me["id"])
    assert mine() is None
    assert store.one("SELECT max_download_bytes AS n FROM user_limits "
                     "WHERE user_id = ?", (me["id"],))["n"] == -1

    accounts.set_limit(store, me["id"], "max_download_bytes", None, me["id"])
    assert mine() == default

    with pytest.raises(ValueError, match="not a per-user limit"):
        accounts.set_limit(store, me["id"], "max_upload_bytes", 10, me["id"])
