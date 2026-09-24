import pytest

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.auth import SCOPES, expand_scope
from siliconcompiler.remote.server.errors import TYPE_BASE, ProblemError


pytest.importorskip("flask", reason="the server extra is not installed")


BASE = "http://localhost/v1"


def slug(response):
    body = response.get_json() or {}
    return (body.get("type") or "").rsplit("/", 1)[-1]


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

def test_the_vocabulary_is_six_values():
    '''Closed and frozen, every one <resource>:read or <resource>:write. It is
    what bounds a stolen token: these and nothing else, ever.'''
    assert set(SCOPES) == {"jobs:read", "jobs:write", "artifacts:read",
                           "devices:read", "devices:write", "profile:read"}
    assert all(s.count(":") == 1 and s.split(":")[1] in ("read", "write")
               for s in SCOPES)


def test_write_carries_read():
    assert expand_scope("jobs:write") == "jobs:read jobs:write"
    assert expand_scope("devices:write") == "devices:read devices:write"


def test_omitting_scope_asks_for_everything_this_profile_grants():
    assert set(expand_scope(None).split()) == set(SCOPES)


def test_an_unknown_scope_is_refused_rather_than_dropped():
    '''Silently dropping it would hand back a token that does less than the
    caller believes.'''
    with pytest.raises(ProblemError) as raised:
        expand_scope("jobs:read jobs:delete")

    assert raised.value.error.slug == "invalid-request"


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

    assert response.status_code == 401
    assert slug(response) == "invalid-dpop-proof"


def test_the_token_endpoint_is_form_encoded(client, key):
    '''RFC 6749's shape, since this borrows the grant.'''
    response = client.post(
        "/v1/auth/token", json={"grant_type": "client_credentials"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")})

    assert response.status_code == 415
    assert slug(response) == "unsupported-media-type"


def test_an_unknown_grant_is_refused(client, key):
    response = client.post(
        "/v1/auth/token", data={"grant_type": "password"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


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

    assert response.status_code == 401
    assert slug(response) == "invalid-dpop-proof"
    # OAuth-shaped at the token endpoint, which is where RFC 6749 puts a client
    # that does not authenticate.
    assert 'invalid_client' in response.headers["WWW-Authenticate"]


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

    assert response.status_code == 401
    assert slug(response) == "invalid-dpop-proof"


def test_a_refresh_may_narrow_and_may_not_widen(client, key):
    first = login(client, key).get_json()

    def refresh(token, scope=None):
        data = {"grant_type": "refresh_token", "refresh_token": token}
        if scope:
            data["scope"] = scope
        return client.post(
            "/v1/auth/token", data=data,
            headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
            content_type="application/x-www-form-urlencoded").get_json()

    narrowed = refresh(first["refresh_token"], "jobs:read")
    assert narrowed["scope"] == "jobs:read"

    widened = refresh(narrowed["refresh_token"], "jobs:write artifacts:read")
    assert widened["scope"] == "jobs:read"


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
    device = call(client, key, "GET", "/v1/devices", token).get_json()["devices"][0]

    assert call(client, key, "DELETE", f"/v1/devices/{device['id']}",
                token).status_code == 204
    assert call(client, key, "GET", "/v1/me", token).status_code == 401


def test_a_device_belonging_to_someone_else_is_not_found(client):
    '''404 rather than 403: a 403 would confirm the id belongs to somebody.'''
    alice, bob = dpop.generate_key(), dpop.generate_key()
    a = login(client, alice, subject="machine:1000").get_json()
    b = login(client, bob, subject="machine:1001").get_json()

    hers = call(client, alice, "GET", "/v1/devices",
                a["access_token"]).get_json()["devices"][0]["id"]

    response = call(client, bob, "GET", f"/v1/devices/{hers}", b["access_token"])

    assert response.status_code == 404
    assert slug(response) == "not-found"


###########################
# The device grant
###########################

def test_the_device_grant_is_routed_and_refuses(client, key):
    '''Routed rather than unrouted, which turns a 404 that means "this server is
    old" into a 501 that means "this deployment never will".'''
    response = client.post(
        "/v1/auth/device", data={},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/device")})

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == "device_grant"


def test_the_device_code_grant_refuses_the_same_way(client, key):
    response = client.post(
        "/v1/auth/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
              "device_code": "whatever"},
        headers={"DPoP": dpop.sign_proof(key, "POST", f"{BASE}/auth/token")},
        content_type="application/x-www-form-urlencoded")

    assert response.status_code == 501
    assert response.get_json()["feature"] == "device_grant"


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
    assert "blocked_reason" not in body


def test_me_carries_the_account_limits(client, key):
    '''Not the same key set as GET /v1's ceiling: five overlap and a client
    combines only those.

    🆕 `auto_fetch_max_bytes` is here as well as on `GET /v1`, and it is the
    reason this block matters to a client at all now: `GET /v1` carries no
    credential, so it cannot vary by caller. The deployment's default is there
    and the value that applies to THIS caller is here.
    '''
    token = login(client, key).get_json()["access_token"]
    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]

    assert set(limits) == {"concurrent_jobs", "concurrent_nodes",
                           "pending_uploads", "max_job_nodes", "devices",
                           "job_retention_days", "auto_fetch_max_bytes"}


def test_me_usage_is_derived_and_reported_only(client, key):
    '''All four numbers come from jobs and artifacts directly; a metering table
    would buy a billing history nobody here bills against.'''
    token = login(client, key).get_json()["access_token"]
    usage = call(client, key, "GET", "/v1/me", token).get_json()["usage"]

    assert set(usage) == {"compute_seconds", "licence_seconds",
                          "storage_bytes", "jobs_active"}
    assert usage["jobs_active"] == 0
    assert usage["compute_seconds"]["limit"] is None
    # Windows are calendar, so resets_at is always a real instant.
    assert usage["compute_seconds"]["resets_at"].endswith("Z")


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
                    token).get_json()["devices"][0]

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
    from siliconcompiler.remote.server import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()

    default = client.get("/v1").get_json()["limits"]["auto_fetch_max_bytes"]
    assert me["limits"]["auto_fetch_max_bytes"] == default

    store = client.application.config["SC_STORE"]
    accounts.set_limit(store, me["id"], "auto_fetch_max_bytes", 1024,
                       me["id"], note="a slow link")

    again = call(client, key, "GET", "/v1/me", token).get_json()
    assert again["limits"]["auto_fetch_max_bytes"] == 1024
    # The deployment's own number is unmoved, and uncredentialed.
    assert client.get("/v1").get_json()["limits"]["auto_fetch_max_bytes"] == default


def test_minus_one_is_unlimited_and_never_reaches_a_client(client, key):
    '''⚠️ The wire had already spent `null` on unlimited while the table needed
    it for *inherit*, so storage uses `-1` and the resolver turns it into the
    wire's `null`.'''
    from siliconcompiler.remote.server import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()
    store = client.application.config["SC_STORE"]

    accounts.set_limit(store, me["id"], "auto_fetch_max_bytes", -1, me["id"])

    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]
    assert limits["auto_fetch_max_bytes"] is None
    assert store.one("SELECT auto_fetch_max_bytes AS n FROM user_limits "
                     "WHERE user_id = ?", (me["id"],))["n"] == -1


def test_a_null_column_inherits_rather_than_meaning_unlimited(client, key):
    '''Sparse: a row can exist and override nothing.'''
    from siliconcompiler.remote.server import accounts

    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()
    store = client.application.config["SC_STORE"]

    accounts.set_limit(store, me["id"], "auto_fetch_max_bytes", 1024, me["id"])
    accounts.set_limit(store, me["id"], "auto_fetch_max_bytes", None, me["id"])

    default = client.get("/v1").get_json()["limits"]["auto_fetch_max_bytes"]
    limits = call(client, key, "GET", "/v1/me", token).get_json()["limits"]
    assert limits["auto_fetch_max_bytes"] == default


def test_only_a_declared_limit_can_be_overridden(client, key):
    '''The column list is not derived from the table, so that adding one is a
    deliberate act rather than an accident.'''
    from siliconcompiler.remote.server import accounts
    import pytest as _pytest

    store = client.application.config["SC_STORE"]
    token = login(client, key).get_json()["access_token"]
    me = call(client, key, "GET", "/v1/me", token).get_json()

    with _pytest.raises(ValueError, match="not a per-user limit"):
        accounts.set_limit(store, me["id"], "max_upload_bytes", 10, me["id"])
