import pytest

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import TYPE_BASE, OAuthError
from siliconcompiler.remote.server.identity.auth import SCOPES, expand_scope


pytest.importorskip("flask", reason="the server extra is not installed")


BASE = "http://localhost/v1"


def slug(response):
    body = response.get_json() or {}
    return (body.get("type") or "").rsplit("/", 1)[-1]


def oauth(response):
    '''The OAuth shape: `error`, and never a problem+json `type`.'''
    body = response.get_json()
    assert "type" not in body, body
    assert response.mimetype == "application/json"
    return body["error"], body.get("reason")


@pytest.fixture
def server():
    from siliconcompiler.remote.server.app import create_app

    return create_app("datadir")


@pytest.fixture
def client(server):
    return server.test_client()


@pytest.fixture
def key():
    return dpop.generate_key()


def login(client, key, subject="machine:1000", **extra):
    form = {"grant_type": "client_credentials",
            "client_id": f"local:{subject}", **extra}
    return client.post(
        "/v1/auth/token", data=form,
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")


def call(client, key, method, path, token, **kwargs):
    url = BASE + path[len("/v1"):]
    return client.open(
        path, method=method,
        headers={"Authorization": f"DPoP {token}",
                 "DPoP": dpop.sign_proof(key, method, url, access_token=token)},
        **kwargs)


###########################
# Scope
###########################

def test_the_vocabulary_is_the_registered_scopes():
    '''Only registered scopes are granted, and every one is
    <resource>:<action>. None is administrative.'''
    assert set(SCOPES) == {"jobs:read", "jobs:write", "jobs:delete", "artifacts:read",
                           "devices:read", "devices:write", "profile:read"}
    assert all(s.count(":") == 1 for s in SCOPES)


def test_write_carries_read():
    assert expand_scope("jobs:write") == "jobs:read jobs:write"
    assert expand_scope("jobs:delete") == "jobs:read jobs:delete"
    assert expand_scope("devices:write") == "devices:read devices:write"


def test_omitting_scope_asks_for_everything_this_profile_grants():
    assert set(expand_scope(None).split()) == set(SCOPES)


def test_an_unknown_scope_is_dropped_and_the_rest_granted():
    '''The response's `scope` says what was granted.'''
    assert expand_scope("jobs:read nosuch:thing") == "jobs:read"


def test_nothing_recognised_left_is_invalid_scope():
    with pytest.raises(OAuthError) as raised:
        expand_scope("nosuch:thing admin:all")

    assert raised.value.error == "invalid_scope"


def test_the_granted_string_is_stable():
    '''Two tokens with the same scope have the same string, so a client can
    compare them.'''
    assert expand_scope("profile:read jobs:read") == \
        expand_scope("jobs:read profile:read")


###########################
# client_credentials
###########################

def test_a_session_with_no_human_involved(client, key):
    response = login(client, key)

    assert response.status_code == 200
    body = response.get_json()

    assert body["token_type"] == "DPoP"      # never Bearer
    assert body["expires_in"] == 900
    assert body["refresh_token"]
    assert set(body["scope"].split()) == set(SCOPES)
    # RFC 6749 makes this a MUST on any response carrying tokens.
    assert response.headers["Cache-Control"] == "no-store"


def test_scope_is_required_on_every_grant(client, key):
    '''A strengthening of RFC 6749, which makes it optional when it equals what
    was asked. Absent would mean "you got what you asked for" on one server and
    "we do not publish this" on another.'''
    assert "scope" in login(client, key).get_json()
    assert "scope" in login(client, key, scope="jobs:read").get_json()


def test_the_token_endpoint_needs_a_proof(client):
    response = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials"},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert oauth(response) == ("invalid_dpop_proof", None)


def test_the_token_endpoint_is_form_encoded(client, key):
    '''RFC 6749's shape, since this borrows the grant -- and a 415 is raised
    before any OAuth processing, so it is problem+json there as everywhere.'''
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


def test_an_unknown_grant_is_unsupported(client, key):
    response = client.post(
        "/v1/auth/token", data={"grant_type": "password"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert oauth(response) == ("unsupported_grant_type", None)


def test_a_malformed_request_is_invalid_request(client, key):
    response = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials",
                                "client_id": "nope"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert oauth(response) == ("invalid_request", None)


def test_unknown_parameters_are_ignored(client, key):
    '''RFC 6749 §3.2: an unknown parameter at the token endpoint is ignored.'''
    response = login(client, key, some_future_parameter="x")

    assert response.status_code == 200


@pytest.mark.parametrize("name", ["actor_token", "audience", "resource"])
def test_the_three_that_would_be_misunderstood_are_refused(client, key, name):
    response = login(client, key, **{name: "x"})

    assert response.status_code == 400
    assert oauth(response) == ("invalid_request", None)


def test_an_unrecognised_scope_is_dropped_and_the_response_says_so(client, key):
    response = login(client, key, scope="jobs:read nosuch:thing")

    assert response.status_code == 200
    assert response.get_json()["scope"] == "jobs:read"


def test_no_recognised_scope_is_invalid_scope(client, key):
    response = login(client, key, scope="nosuch:thing")

    assert response.status_code == 400
    assert oauth(response) == ("invalid_scope", None)


###########################
# The binding
###########################

def test_first_contact_records_the_key(client, key, server):
    login(client, key)

    device = server.config["SC_STORE"].one("SELECT * FROM devices")
    assert device["dpop_jkt"] == dpop.jwk_thumbprint(dpop.public_jwk(key))
    assert server.config["SC_STORE"].one(
        "SELECT kind FROM device_events")["kind"] == "enrolled"


def test_one_user_cannot_claim_another(client, key):
    '''Without the binding, A on a shared machine presents B's derivation with
    A's own key and gets a session as B -- and the derivation is public
    knowledge, so the claim costs nothing to forge.'''
    login(client, key, subject="machine:1001")

    mallory = dpop.generate_key()
    response = login(client, mallory, subject="machine:1001")

    # OAuth-shaped at the token endpoint, which is where RFC 6749 puts a client
    # that does not authenticate; and it says why, so a person can ask.
    assert response.status_code == 401
    assert oauth(response) == ("invalid_client", None)
    assert "bound to a different key" in response.get_json()["error_description"]


def test_the_operator_can_release_a_binding(client, key, server):
    '''The recovery path is a person, not an automatic rebind: the registry
    CLI's release-binding frees the subject to enrol a new key.'''
    from siliconcompiler.remote.server.software import registry

    login(client, key, subject="machine:1001")
    replacement = dpop.generate_key()
    assert login(client, replacement, subject="machine:1001").status_code == 401

    assert registry.main(["-datadir", str(server.config["SC_DATADIR"]),
                          "release-binding", "machine:1001"]) == 0

    assert login(client, replacement, subject="machine:1001").status_code == 200


def test_a_refused_rebind_is_recorded(client, key, server):
    login(client, key, subject="machine:1001")
    login(client, dpop.generate_key(), subject="machine:1001")

    kinds = [row["kind"] for row in
             server.config["SC_STORE"].all("SELECT kind FROM device_events")]
    assert "reauth_failed" in kinds


def test_binding_can_be_turned_off_for_a_container_fleet():
    '''/etc/machine-id is per image, so every container derives the same
    subject: with binding on the first one binds and every later one is
    refused. Turning it off declares the deployment a single trust domain.'''
    from siliconcompiler.remote.server.app import create_app

    app = create_app("datadir", bind_keys=False)
    client = app.test_client()

    login(client, dpop.generate_key(), subject="image:1000")
    second = login(client, dpop.generate_key(), subject="image:1000")

    assert second.status_code == 200


def test_two_subjects_are_two_identities(client):
    '''A machine-only key would collapse every user on a login node into one
    identity, and B could cancel A's jobs.'''
    alice, bob = dpop.generate_key(), dpop.generate_key()

    a = login(client, alice, subject="machine:1000").get_json()
    b = login(client, bob, subject="machine:1001").get_json()

    alice_id = call(client, alice, "GET", "/v1/me", a["access_token"]).get_json()["id"]
    bob_id = call(client, bob, "GET", "/v1/me", b["access_token"]).get_json()["id"]

    assert alice_id != bob_id


###########################
# Presenting a token
###########################

def test_a_token_is_useless_without_its_key(client, key):
    '''The whole point of DPoP: a stolen access token proves nothing on its
    own.'''
    token = login(client, key).get_json()["access_token"]

    response = call(client, dpop.generate_key(), "GET", "/v1/me", token)

    assert response.status_code == 401
    assert slug(response) == "invalid-dpop-proof"


def test_a_token_with_no_proof_is_refused(client, key):
    token = login(client, key).get_json()["access_token"]

    response = client.get("/v1/me", headers={"Authorization": f"DPoP {token}"})

    assert response.status_code == 401
    assert slug(response) == "invalid-dpop-proof"


def test_no_credential_carries_a_challenge(client):
    response = client.get("/v1/me")

    assert response.status_code == 401
    assert slug(response) == "invalid-token"
    assert response.headers["WWW-Authenticate"].startswith("DPoP")


def test_a_proof_cannot_be_replayed(client, key):
    '''One proof, one request.'''
    token = login(client, key).get_json()["access_token"]
    proof = dpop.sign_proof(key, "GET", f"{BASE}/me", access_token=token)
    headers = {"Authorization": f"DPoP {token}", "DPoP": proof}

    assert client.get("/v1/me", headers=headers).status_code == 200

    replayed = client.get("/v1/me", headers=headers)
    assert replayed.status_code == 401
    assert slug(replayed) == "invalid-dpop-proof"


def test_one_proof_sent_twice_at_once_is_taken_once(server, key):
    '''🔴 Requests run on threads of their own: two arriving together with one
    proof must not both read it as unseen. The check is widened here so the
    two always overlap.'''
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
    '''The client fails rather than refreshing: a refresh re-mints the same
    ceiling, so retrying is a loop.'''
    token = login(client, key, scope="jobs:read").get_json()["access_token"]

    response = call(client, key, "GET", "/v1/me", token)

    assert response.status_code == 403
    assert slug(response) == "insufficient-scope"
    assert 'scope="profile:read"' in response.headers["WWW-Authenticate"]


###########################
# Refresh
###########################

def test_a_refresh_rotates_the_session(client, key):
    first = login(client, key).get_json()

    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "refresh_token",
              "refresh_token": first["refresh_token"]},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 200
    assert response.get_json()["refresh_token"] != first["refresh_token"]


def test_a_refresh_is_bound_to_the_key(client, key):
    '''Where a stolen refresh token stops being useful to anything that does
    not also hold the key.'''
    first = login(client, key).get_json()

    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "refresh_token",
              "refresh_token": first["refresh_token"]},
        headers={"DPoP": dpop.sign_proof(dpop.generate_key(), "POST",
                                         f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert oauth(response) == ("invalid_dpop_proof", None)


def refreshing(client, token, signer, **extra):
    return client.post(
        "/v1/auth/token",
        data={"grant_type": "refresh_token", "refresh_token": token, **extra},
        headers={"DPoP": dpop.sign_proof(signer, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")


def test_a_refresh_returns_the_full_scope_whatever_it_asks(client, key, server):
    '''Rule 3: a server never narrows a session on refresh, and never writes a
    narrowed scope into the family.'''
    first = login(client, key, scope="jobs:write profile:read").get_json()
    assert first["scope"] == "jobs:read jobs:write profile:read"

    again = refreshing(client, first["refresh_token"], key, scope="jobs:read").get_json()

    assert again["scope"] == "jobs:read jobs:write profile:read"
    assert server.config["SC_STORE"].one("SELECT scope FROM token_families")["scope"] == \
        "jobs:read jobs:write profile:read"


def test_replaying_a_refresh_inside_the_grace_window_is_not_an_attack(client, key):
    '''A client whose response was lost retries with a token the server has
    already rotated. Killing its session for that would be punishing a dropped
    packet.'''
    first = login(client, key).get_json()

    def refresh():
        return client.post(
            "/v1/auth/token",
            data={"grant_type": "refresh_token",
                  "refresh_token": first["refresh_token"]},
            headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
            content_type="application/x-www-form-urlencoded")

    assert refresh().status_code == 200
    assert refresh().status_code == 200


def test_a_lost_response_is_answered_with_the_same_pair(client, key, server):
    '''🔴 The replacement already issued, and never a second live refresh
    token in the family.'''
    first = login(client, key).get_json()

    one = refreshing(client, first["refresh_token"], key).get_json()
    two = refreshing(client, first["refresh_token"], key).get_json()

    assert one["refresh_token"] == two["refresh_token"]
    live = server.config["SC_STORE"].all(
        "SELECT jti FROM refresh_tokens WHERE replaced_at IS NULL")
    assert len(live) == 1


def test_a_repeat_after_the_window_ends_the_session_as_reused(client, key, server):
    from siliconcompiler.remote.server.identity import auth

    first = login(client, key).get_json()
    second = refreshing(client, first["refresh_token"], key).get_json()
    server.config["SC_STORE"].execute(
        "UPDATE refresh_tokens SET replaced_at = '2020-01-01T00:00:00.000Z' "
        "WHERE replaced_at IS NOT NULL")

    assert auth.REFRESH_GRACE_SECONDS >= 120          # a few minutes
    response = refreshing(client, first["refresh_token"], key)

    assert response.status_code == 400
    assert oauth(response) == ("invalid_grant", "reused")
    # The whole family: the current token is dead too.
    assert oauth(refreshing(client, second["refresh_token"], key)) == \
        ("invalid_grant", "reused")
    assert server.config["SC_STORE"].one(
        "SELECT revoked_reason FROM token_families")["revoked_reason"] == "reuse_detected"


def test_an_ended_session_is_invalid_grant_with_its_reason(client, key):
    first = login(client, key).get_json()
    call(client, key, "POST", "/v1/auth/revoke", first["access_token"])

    response = refreshing(client, first["refresh_token"], key)

    assert oauth(response) == ("invalid_grant", "revoked")


def test_an_unknown_refresh_token_is_invalid_grant(client, key):
    assert oauth(refreshing(client, "not-a-token", key)) == ("invalid_grant", None)


def test_a_changed_fingerprint_steps_up_and_revokes_nothing(client, key, server):
    '''Identity §6: a wrong fingerprint with a valid key is a machine that
    changed. Refused `invalid_grant` with no reason, and the session lives.'''
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


def test_an_old_refresh_with_another_keys_proof_revokes_nothing(client, key):
    '''🔴 Identity D56: reuse is judged only after the refresh's proof
    verifies. Otherwise anyone holding a leaked, long-rotated token could end
    the owner's session without the key.'''
    def refresh(token, signer):
        return client.post(
            "/v1/auth/token",
            data={"grant_type": "refresh_token", "refresh_token": token},
            headers={"DPoP": dpop.sign_proof(signer, "POST", f"{BASE}/auth/token")},
            content_type="application/x-www-form-urlencoded")

    first = login(client, key).get_json()["refresh_token"]
    second = refresh(first, key).get_json()["refresh_token"]
    third = refresh(second, key).get_json()["refresh_token"]

    stolen = refresh(first, dpop.generate_key())

    assert stolen.status_code == 400
    assert oauth(stolen) == ("invalid_dpop_proof", None)
    # And the family lives: the owner's current token still refreshes.
    assert refresh(third, key).status_code == 200


###########################
# Ending a session
###########################

def test_revoke_needs_no_scope(client, key):
    '''A credential may always end itself. A logout that can be scoped away is
    a session nobody can close.'''
    token = login(client, key, scope="jobs:read").get_json()["access_token"]

    assert call(client, key, "POST", "/v1/auth/revoke", token).status_code == 204


def test_a_revoked_session_says_so_in_the_wire_vocabulary(client, key, server):
    '''Three stored reasons collapse to one client branch. The column records
    why for an operator; the wire says what to do.'''
    token = login(client, key).get_json()["access_token"]
    call(client, key, "POST", "/v1/auth/revoke", token)

    response = call(client, key, "GET", "/v1/me", token)

    assert response.status_code == 401
    assert slug(response) == "session-ended"
    assert response.get_json()["reason"] in ("revoked", "deactivated", "expired")

    # And the store keeps the operator's version.
    assert server.config["SC_STORE"].one(
        "SELECT revoked_reason FROM token_families")["revoked_reason"] == "user_logout"


def test_revoking_a_device_ends_its_sessions(client, key):
    token = login(client, key).get_json()["access_token"]
    device = call(client, key, "GET", "/v1/devices", token).get_json()["items"][0]

    assert call(client, key, "DELETE", f"/v1/devices/{device['id']}",
                token).status_code == 204
    assert call(client, key, "GET", "/v1/me", token).status_code == 401


def test_a_device_belonging_to_someone_else_is_not_found(client):
    '''404 rather than 403: a 403 would confirm the id belongs to somebody.'''
    alice, bob = dpop.generate_key(), dpop.generate_key()
    a = login(client, alice, subject="machine:1000").get_json()
    b = login(client, bob, subject="machine:1001").get_json()

    hers = call(client, alice, "GET", "/v1/devices",
                a["access_token"]).get_json()["items"][0]["id"]

    response = call(client, bob, "GET", f"/v1/devices/{hers}", b["access_token"])

    assert response.status_code == 404
    assert slug(response) == "not-found"


###########################
# The device grant
###########################

def test_the_device_grant_is_routed_and_refuses(client, key):
    '''Routed rather than unrouted, and in the OAuth shape: the login
    algorithm's cue to use client_credentials.'''
    response = client.post(
        "/v1/auth/device", data={"scope": " ".join(SCOPES)},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/device")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert oauth(response) == ("unsupported_grant_type", None)


@pytest.mark.parametrize("grant", ["urn:ietf:params:oauth:grant-type:device_code",
                                   "urn:ietf:params:oauth:grant-type:token-exchange"])
def test_the_grants_this_profile_lacks_refuse_the_same_way(client, key, grant):
    response = client.post(
        "/v1/auth/token",
        data={"grant_type": grant, "device_code": "whatever"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert oauth(response) == ("unsupported_grant_type", None)


###########################
# Configured public origins
###########################

@pytest.mark.parametrize("signed", ["https://sc.example.test", "http://lab.test:8080"])
def test_the_scheme_a_request_arrived_on_is_its_htus_origin(tmp_path, signed):
    '''🔴 Contract rule 5 (D70): the configured public origin a request
    matched, by its DPoP `htu` -- never the socket's, which behind a
    TLS-terminating proxy is http whichever origin the client used.'''
    import json

    from siliconcompiler.remote.server.app import create_app

    datadir = tmp_path / "both"
    datadir.mkdir()
    (datadir / "config.json").write_text(json.dumps(
        {"public_origins": ["http://lab.test:8080", "https://sc.example.test"]}))
    client = create_app(datadir).test_client()
    key = dpop.generate_key()
    # What the proxy forwards either way: plain http, to the backend's Host.
    backend = {"Host": "lab.test:8080"}

    def proof(method, path, token=None):
        return dpop.sign_proof(key, method, f"{signed}{path}", access_token=token)

    token = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials",
                                "client_id": "local:machine:1000"},
        headers={"DPoP": proof("POST", "/v1/auth/token"), **backend},
        content_type="application/x-www-form-urlencoded").get_json()["access_token"]
    page = client.post("/v1/auth/browser", json={}, headers={
        "Authorization": f"DPoP {token}", **backend,
        "DPoP": proof("POST", "/v1/auth/browser", token)}).get_json()

    assert page["url"].startswith(f"{signed}/portal/enter?token=")


def test_htu_and_handed_out_urls_come_from_config_behind_a_proxy(tmp_path):
    '''A proxy rewrites `Host`; the server checks proofs against, and builds
    URLs on, the origin it is configured with -- never the header.'''
    import json

    from siliconcompiler.remote.server.app import create_app

    datadir = tmp_path / "proxied"
    datadir.mkdir()
    (datadir / "config.json").write_text(json.dumps(
        {"public_origins": ["https://sc.example.test"]}))
    app = create_app(datadir)
    client = app.test_client()
    key = dpop.generate_key()
    public = "https://sc.example.test/v1"
    backend = {"Host": "backend:8080"}

    token = client.post(
        "/v1/auth/token", data={"grant_type": "client_credentials",
                                "client_id": "local:machine:1000"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{public}/auth/token"), **backend},
        content_type="application/x-www-form-urlencoded").get_json()["access_token"]

    def authed(method, path, **kwargs):
        return client.open(path, method=method, headers={
            "Authorization": f"DPoP {token}", **backend,
            "DPoP": dpop.sign_proof(key, method, "https://sc.example.test" + path,
                                    access_token=token)}, **kwargs)

    job = authed("POST", "/v1/jobs", json={"design": "gcd", "jobname": "job0"}).get_json()
    grant = authed("POST", f"/v1/jobs/{job['id']}/upload-grant",
                   json={"size_bytes": 10, "digest": "sha256:" + "0" * 64}).get_json()
    assert grant["url"].startswith("https://sc.example.test/storage/upload/")

    page = authed("POST", "/v1/auth/browser", json={}).get_json()
    assert page["url"].startswith("https://sc.example.test/portal/")

    # A proof made for the Host the proxy wrote is not a proof for this server.
    wrong = client.get("/v1/me", headers={
        "Authorization": f"DPoP {token}", **backend,
        "DPoP": dpop.sign_proof(key, "GET", "http://backend:8080/v1/me",
                                access_token=token)})
    assert wrong.status_code == 401
    assert slug(wrong) == "invalid-dpop-proof"


###########################
# GET /v1/me
###########################

def test_me_omits_authorized_and_sends_empty_projects(client, key):
    '''`authorized` is omitted whole rather than sent empty: {} would claim
    "you were granted nothing" where the truth is "this server does not do
    grants". `projects` is the opposite rule, and deliberate.'''
    token = login(client, key).get_json()["access_token"]
    body = call(client, key, "GET", "/v1/me", token).get_json()

    assert "authorized" not in body
    assert body["projects"] == []
    assert body["terms"] == []
    assert body["can_submit"] is True
    assert "blocked_type" not in body


def test_me_carries_the_account_limits(client, key):
    '''🔴 Seven members, the caller's effective values: the server combines
    the two blocks, and a client reads the account's limits here alone.

    `max_download_bytes` is here as well as on `GET /v1`: `GET /v1` carries no
    credential, so it cannot vary by caller. The deployment's default is there
    and the value that applies to THIS caller is here.
    '''
    token = login(client, key).get_json()["access_token"]
    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]

    assert set(limits) == {"concurrent_jobs", "concurrent_nodes",
                           "pending_uploads", "max_job_nodes", "devices",
                           "artifact_retention_seconds", "max_download_bytes",
                           "max_staging_seconds"}
    assert limits["artifact_retention_seconds"] == 2592000
    assert limits["max_staging_seconds"] == 3600


def test_me_usage_is_derived_and_reported_only(client, key):
    '''All four numbers come from jobs and artifacts directly; a metering table
    would buy a billing history nobody here bills against.'''
    token = login(client, key).get_json()["access_token"]
    usage = call(client, key, "GET", "/v1/me", token).get_json()["usage"]

    assert set(usage) == {"compute_seconds", "license_seconds",
                          "storage_bytes", "concurrent_jobs"}
    assert usage["concurrent_jobs"] == 0
    assert usage["compute_seconds"]["limit"] is None
    # No license is metered here, and there is no per-tool row to report.
    assert usage["license_seconds"] == {}
    # Windows are calendar, so resets_at is always a real instant.
    assert usage["compute_seconds"]["resets_at"].endswith("Z")


def test_me_usage_carries_total_beside_used(client, key):
    '''`used` this calendar month, `total` everything recorded -- and `null`
    on a stock, whose `used` is already the whole (entitlements §3; D74).'''
    token = login(client, key).get_json()["access_token"]
    usage = call(client, key, "GET", "/v1/me", token).get_json()["usage"]

    for member in ("used", "total", "limit", "window", "resets_at"):
        assert member in usage["compute_seconds"], member
        assert member in usage["storage_bytes"], member
    assert usage["compute_seconds"]["total"] == 0
    assert usage["storage_bytes"]["total"] is None
    assert usage["storage_bytes"]["window"] is None
    assert usage["storage_bytes"]["resets_at"] is None


def test_me_carries_the_session_the_request_was_made_in(client, key, server):
    '''🔴 From the calling token's family and device, every member REQUIRED
    (surface §5; D276), and reading it rotates nothing.'''
    first = login(client, key).get_json()
    session = call(client, key, "GET", "/v1/me", first["access_token"]).get_json()["session"]

    assert session["kind"] == "interactive"
    assert session["scope"] == first["scope"]
    device = call(client, key, "GET", "/v1/devices", first["access_token"]) \
        .get_json()["items"][0]["id"]
    assert session["device_id"] == device
    for member in ("access_expires_at", "refresh_expires_at", "session_expires_at"):
        assert session[member].endswith("Z"), member
    assert session["refresh_expires_at"] <= session["session_expires_at"]

    # Nothing rotated: the refresh token still refreshes.
    assert refreshing(client, first["refresh_token"], key).status_code == 200


def test_a_ci_session_has_no_device_and_no_refresh(server):
    '''The shape a CI session takes, from its family: `device_id` null, and
    `refresh_expires_at` null where there is no refresh token. `sc-server`
    mints none itself -- CI credentials are crucible's -- so its family is
    written here as crucible writes one.'''
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

    assert (view["kind"], view["device_id"], view["refresh_expires_at"]) == \
        ("ci", None, None)
    assert view["scope"] == "jobs:read jobs:write"
    assert view["session_expires_at"] == "2026-12-01T00:00:00.000Z"


def test_authenticated_responses_are_never_cacheable(client, key):
    '''A cache rule that matched /v1/* would serve one caller's response to
    another's request.'''
    token = login(client, key).get_json()["access_token"]

    for path in ("/v1/me", "/v1/devices"):
        response = call(client, key, "GET", path, token)
        assert response.headers["Cache-Control"] == "private, no-store"


def test_the_registry_uri_is_the_frozen_namespace(client):
    '''It belongs to SiliconCompiler rather than to a deployment: both
    implementations must return the same URI or a client cannot branch across
    them.'''
    body = client.get("/v1/nothing-here").get_json()

    assert body["type"].startswith(f"{TYPE_BASE}/")
    assert TYPE_BASE == "https://siliconcompiler.com/server-errors"


###########################
# The same key, a new derivation
###########################

def test_a_changed_derivation_mints_a_new_identity(client, key):
    '''🔴 A reimaged host, a rebuilt container, a changed uid or a client
    release that moves the salt all present the SAME key under a NEW subject.

    The device row for the old identity still holds this thumbprint, which is
    unique across live devices -- so before this was handled the insert raised
    an IntegrityError and the one endpoint a client cannot get past answered
    500 with an HTML body.
    '''
    first = login(client, key, subject="machine-old:1000")
    assert first.status_code == 200
    was = call(client, key, "GET", "/v1/me", first.get_json()["access_token"]) \
        .get_json()["id"]

    second = login(client, key, subject="machine-new:1000")
    assert second.status_code == 200

    now = call(client, key, "GET", "/v1/me", second.get_json()["access_token"]) \
        .get_json()["id"]
    assert now != was


def test_the_previous_enrolment_ends_rather_than_lingering(client, key):
    '''One live device per key. The old session is over, and it says so with
    the slug that means re-authenticate and do NOT refresh.'''
    first = login(client, key, subject="machine-old:1000")
    stale_token = first.get_json()["access_token"]

    login(client, key, subject="machine-new:1000")

    response = call(client, key, "GET", "/v1/me", stale_token)
    assert response.status_code == 401
    assert slug(response) == "session-ended"


def test_the_retirement_is_recorded(server, client, key):
    '''device_events is append-only and is the half of this story with a
    reader: a machine that changed who it is should be visible afterwards.'''
    login(client, key, subject="machine-old:1000")
    login(client, key, subject="machine-new:1000")

    kinds = [row["kind"] for row in server.config["SC_STORE"].all(
        "SELECT kind FROM device_events ORDER BY id")]
    assert kinds == ["enrolled", "revoked", "enrolled"]


def test_the_new_identity_sees_none_of_the_old_ones_jobs(client, key):
    '''Which is the whole reason the client warns about it: the jobs did not go
    anywhere, and the person asking is no longer their owner.'''
    old = login(client, key, subject="machine-old:1000").get_json()["access_token"]
    call(client, key, "POST", "/v1/jobs", old,
         json={"design": "gcd", "jobname": "job0"})

    new = login(client, key, subject="machine-new:1000").get_json()["access_token"]

    assert call(client, key, "GET", "/v1/jobs", new).get_json()["items"] == []


def test_a_refresh_counts_as_the_device_being_seen(client, key):
    '''🔴 A rotation is the only signal most devices ever give.

    The client refreshes rather than logging in again -- deliberately, so a
    session lasts its twelve days instead of minting a family per command -- so
    writing this only at `client_credentials` left `last_seen_at` NULL for a
    machine that had been running jobs all day.
    '''
    from conftest import call

    granted = login(client, key).get_json()

    def devices(token):
        return call(client, key, "GET", "/v1/devices",
                    token).get_json()["items"][0]

    first = devices(granted["access_token"])["last_seen_at"]
    assert first is not None

    rotated = client.post(
        "/v1/auth/token",
        data={"grant_type": "refresh_token",
              "refresh_token": granted["refresh_token"]},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded").get_json()

    assert devices(rotated["access_token"])["last_seen_at"] >= first


###########################
# A ceiling that differs per account
###########################

def test_an_override_reaches_the_caller_and_not_the_capabilities(client, key):
    '''🔴 `GET /v1` carries no credential, so it cannot vary by caller. The
    deployment's default lives there and the value that applies to THIS caller
    lives in the identity block -- which is why a per-user ceiling had to be
    published on `/v1/me` at all.'''
    from siliconcompiler.remote.server.identity import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()

    default = client.get("/v1").get_json()["limits"]["max_download_bytes"]
    assert me["limits"]["max_download_bytes"] == default

    store = client.application.config["SC_STORE"]
    accounts.set_limit(store, me["id"], "max_download_bytes", 1024,
                       me["id"], note="a slow link")

    again = call(client, key, "GET", "/v1/me", token).get_json()
    assert again["limits"]["max_download_bytes"] == 1024
    # The deployment's own number is unmoved, and uncredentialed.
    assert client.get("/v1").get_json()["limits"]["max_download_bytes"] == default


def test_minus_one_is_unlimited_and_never_reaches_a_client(client, key):
    '''⚠️ The wire had already spent `null` on unlimited while the table needed
    it for *inherit*, so storage uses `-1` and the resolver turns it into the
    wire's `null`.'''
    from siliconcompiler.remote.server.identity import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()
    store = client.application.config["SC_STORE"]

    accounts.set_limit(store, me["id"], "max_download_bytes", -1, me["id"])

    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]
    assert limits["max_download_bytes"] is None
    assert store.one("SELECT max_download_bytes AS n FROM user_limits "
                     "WHERE user_id = ?", (me["id"],))["n"] == -1


def test_a_null_column_inherits_rather_than_meaning_unlimited(client, key):
    '''Sparse: a row can exist and override nothing.'''
    from siliconcompiler.remote.server.identity import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()
    store = client.application.config["SC_STORE"]

    accounts.set_limit(store, me["id"], "max_download_bytes", 1024, me["id"])
    accounts.set_limit(store, me["id"], "max_download_bytes", None, me["id"])

    default = client.get("/v1").get_json()["limits"]["max_download_bytes"]
    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]
    assert limits["max_download_bytes"] == default


def test_only_a_declared_limit_can_be_overridden(client, key):
    '''The column list is not derived from the table, so that adding one is a
    deliberate act rather than an accident.'''
    from siliconcompiler.remote.server.identity import accounts
    import pytest as _pytest

    store = client.application.config["SC_STORE"]
    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()

    with _pytest.raises(ValueError, match="not a per-user limit"):
        accounts.set_limit(store, me["id"], "max_upload_bytes", 10, me["id"])


def test_the_refresh_grace_window_is_300_seconds():
    '''This deployment's value for the contract's "a few minutes" (profile §6,
    *The refresh grace window is 300 seconds*).'''
    from siliconcompiler.remote.server.identity import auth

    assert auth.REFRESH_GRACE_SECONDS == 300


@pytest.mark.parametrize("address", ["127.0.0.1", "::1"])
def test_a_changed_key_is_refused_on_a_local_connection_too(client, key, address):
    '''Re-registration is never automatic (profile §7): a known subject with
    a different key is `invalid_client` wherever it comes from, loopback
    included, and the operator releasing the binding is the one way back.'''
    client.environ_base["REMOTE_ADDR"] = address
    login(client, key, subject="machine:1001")

    response = login(client, dpop.generate_key(), subject="machine:1001")

    assert response.status_code == 401
    assert oauth(response) == ("invalid_client", None)


def test_a_session_ends_for_the_registrys_reasons_and_no_other():
    '''`session-ended`'s `reason` is a closed set: every cause the store
    records maps onto one, and each has its own sentence.'''
    from siliconcompiler.remote.server.identity import auth
    # Why a session is over, as the registry has it. All four are one client
    # branch -- re-authenticate, and do NOT refresh.
    SESSION_END_REASONS = ("revoked", "reused", "deactivated", "expired")

    assert set(auth._ENDED) == set(SESSION_END_REASONS)
    assert set(auth._WIRE_REASON.values()) <= set(SESSION_END_REASONS)


@pytest.mark.parametrize("signed", ["http://LOCALHOST/v1/me", "http://localhost:80/v1/me",
                                    "HTTP://Localhost:80/v1/me"])
def test_a_proof_signed_for_a_canonical_equivalent_is_accepted(server_client, key, token,
                                                               signed):
    '''🔴 Identity *The proof rules*: this server canonicalises the proof's
    `htu` and its configured origin with the request's path before comparing,
    so a client that signed `:80` or a mixed-case host is still accepted.'''
    from test_dpop import proof_with_htu

    response = server_client.get("/v1/me", headers={
        "Authorization": f"DPoP {token}",
        "DPoP": proof_with_htu(key, "GET", signed, access_token=token)})

    assert response.status_code == 200, response.get_json()
