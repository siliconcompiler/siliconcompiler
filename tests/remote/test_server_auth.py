import time

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote import dpop  # noqa: E402

from conftest import call, login, proof, slug  # noqa: E402


def _refresh(client, key, refresh_token, signed_with=None):
    return client.post(
        "/v1/auth/token", data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"DPoP": proof(signed_with or key, "POST", "/v1/auth/token")})


def test_a_login_answers_with_a_session(server_client, key):
    response = login(server_client, key)

    body = response.get_json()
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert body["token_type"] == "DPoP"
    assert body["expires_in"] == 900
    assert body["access_token"] != body["refresh_token"]
    assert set(body["scope"].split()) >= {"jobs:read", "profile:read", "devices:write"}


@pytest.mark.parametrize("form, headers, status, error", [
    ({"grant_type": "client_credentials", "client_id": "local:x"}, {}, 400,
     "invalid_dpop_proof"),
    ({"grant_type": "client_credentials", "client_id": "local:x"}, {"DPoP": "junk"}, 400,
     "invalid_dpop_proof"),
    ({"grant_type": "client_credentials", "client_id": "machine:x"}, None, 400,
     "invalid_request"),
    ({"grant_type": "client_credentials", "client_id": "local:"}, None, 400,
     "invalid_request"),
    ({"grant_type": "refresh_token"}, None, 400, "invalid_request"),
    ({}, None, 400, "invalid_request"),
    ({"grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, None, 400,
     "unsupported_grant_type"),
])
def test_the_token_endpoint_refuses_in_the_oauth_shape(server_client, key, form, headers,
                                                       status, error):
    if headers is None:
        headers = {"DPoP": proof(key, "POST", "/v1/auth/token")}

    response = server_client.post("/v1/auth/token", data=form, headers=headers)

    assert response.status_code == status
    assert response.get_json()["error"] == error
    assert response.get_json()["error_description"]


def test_a_proof_is_good_once(server_client, key):
    headers = {"DPoP": proof(key, "POST", "/v1/auth/token")}
    form = {"grant_type": "client_credentials", "client_id": "local:x"}

    assert server_client.post("/v1/auth/token", data=form, headers=headers).status_code == 200
    again = server_client.post("/v1/auth/token", data=form, headers=headers)

    assert again.get_json()["error"] == "invalid_dpop_proof"


def test_a_subject_is_bound_to_the_first_key_until_its_device_is_revoked(server_client, key):
    first = login(server_client, key).get_json()
    other = dpop.generate_key()

    refused = login(server_client, other)
    assert refused.status_code == 401
    assert refused.get_json()["error"] == "invalid_client"
    # The same key again is the same device.
    assert login(server_client, key).status_code == 200
    # Another subject is another user.
    assert login(server_client, other, subject="machine:1001").status_code == 200

    device = call(server_client, key, "GET", "/v1/devices", first["access_token"]
                  ).get_json()["items"][0]["id"]
    assert call(server_client, key, "DELETE", f"/v1/devices/{device}",
                first["access_token"]).status_code == 204
    assert login(server_client, other).status_code == 200


def test_a_refresh_rotates_and_the_old_token_stops_working(server_client, key):
    first = login(server_client, key).get_json()

    second = _refresh(server_client, key, first["refresh_token"])
    assert second.status_code == 200
    assert second.get_json()["refresh_token"] != first["refresh_token"]
    assert call(server_client, key, "GET", "/v1/me", second.get_json()["access_token"]
                ).status_code == 200

    old = _refresh(server_client, key, first["refresh_token"])
    assert old.status_code == 400
    assert old.get_json()["error"] == "invalid_grant"
    assert "reason" not in old.get_json()


def test_a_refresh_token_needs_its_key(server_client, key):
    first = login(server_client, key).get_json()

    stolen = _refresh(server_client, key, first["refresh_token"], signed_with=dpop.generate_key())

    assert stolen.get_json()["error"] == "invalid_dpop_proof"
    # Refused before it was spent.
    assert _refresh(server_client, key, first["refresh_token"]).status_code == 200


def test_a_revoked_session_cannot_be_refreshed_and_says_so(server_client, key):
    first = login(server_client, key).get_json()

    assert call(server_client, key, "POST", "/v1/auth/revoke", first["access_token"]
                ).status_code == 204

    refused = _refresh(server_client, key, first["refresh_token"])
    assert refused.get_json()["error"] == "invalid_grant"
    assert refused.get_json()["reason"] == "revoked"

    ended = call(server_client, key, "GET", "/v1/me", first["access_token"])
    assert ended.status_code == 401
    assert slug(ended) == "session-ended"
    assert ended.get_json()["reason"] == "revoked"
    assert 'error="invalid_token"' in ended.headers["WWW-Authenticate"]


def test_me_says_who_and_what_session(server_client, key, token):
    body = call(server_client, key, "GET", "/v1/me", token).get_json()

    assert body["issuer"] == "local"
    assert body["can_submit"] is True
    assert body["limits"]["max_download_bytes"] == 100 << 20
    assert body["session"]["kind"] == "interactive"
    for member in ("access_expires_at", "refresh_expires_at", "session_expires_at"):
        assert body["session"][member].endswith("Z")
    # The same subject is the same user, on any session.
    again = login(server_client, key).get_json()["access_token"]
    assert call(server_client, key, "GET", "/v1/me", again).get_json()["id"] == body["id"]


def _proof_for(key, token):
    return lambda method, path: {"Authorization": f"DPoP {token}",
                                 "DPoP": proof(key, method, path, token)}


@pytest.mark.parametrize("case, status, expected, challenge", [
    ("no credential", 401, "invalid-token", "DPoP"),
    ("no proof", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
    ("unknown token", 401, "invalid-token", 'DPoP error="invalid_token"'),
    ("expired token", 401, "invalid-token", 'DPoP error="invalid_token"'),
    ("another key", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
    ("another path", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
    ("another method", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
    ("another token", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
    ("replayed", 401, "invalid-dpop-proof", 'DPoP error="invalid_dpop_proof"'),
])
def test_an_authenticated_request_is_refused_by_what_is_wrong_with_it(
        server, server_client, key, token, case, status, expected, challenge):
    headers = _proof_for(key, token)("GET", "/v1/me")
    if case == "no credential":
        headers = {}
    elif case == "no proof":
        del headers["DPoP"]
    elif case == "unknown token":
        headers = _proof_for(key, "unknown")("GET", "/v1/me")
    elif case == "expired token":
        server.config["SC_STORE"].execute("UPDATE tokens SET expires_at = ?", (time.time() - 1,))
    elif case == "another key":
        headers = _proof_for(dpop.generate_key(), token)("GET", "/v1/me")
    elif case == "another path":
        headers = _proof_for(key, token)("GET", "/v1/devices")
    elif case == "another method":
        headers = _proof_for(key, token)("POST", "/v1/me")
    elif case == "another token":
        headers["DPoP"] = proof(key, "GET", "/v1/me", "another")
    elif case == "replayed":
        assert server_client.get("/v1/me", headers=headers).status_code == 200

    response = server_client.get("/v1/me", headers=headers)

    assert response.status_code == status
    assert slug(response) == expected
    assert response.headers["WWW-Authenticate"] == challenge


def test_revoking_a_device_ends_its_sessions_and_only_its_owner_may(server_client, key, token):
    stranger = dpop.generate_key()
    theirs = login(server_client, stranger, subject="machine:1001").get_json()["access_token"]
    mine = call(server_client, key, "GET", "/v1/devices", token).get_json()["items"]

    assert len(mine) == 1 and mine[0]["current"] is True
    assert call(server_client, stranger, "DELETE", f"/v1/devices/{mine[0]['id']}",
                theirs).status_code == 404

    assert call(server_client, key, "DELETE", f"/v1/devices/{mine[0]['id']}",
                token).status_code == 204
    assert slug(call(server_client, key, "GET", "/v1/me", token)) == "session-ended"
    assert call(server_client, stranger, "GET", "/v1/me", theirs).status_code == 200


def test_the_device_grant_is_not_offered(server_client, key):
    response = server_client.post("/v1/auth/device", data={"client_id": "x"})

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"


def test_a_configured_origin_is_what_a_proof_names(key):
    from conftest import BASE
    from siliconcompiler.remote.server.app import create_app

    client = create_app("sc-server", public_origins=["https://sc.example"]).test_client()
    form = {"grant_type": "client_credentials", "client_id": "local:x"}

    refused = client.post("/v1/auth/token", data=form, headers={
        "DPoP": dpop.sign_proof(key, "POST", BASE + "/v1/auth/token")})
    assert refused.get_json()["error"] == "invalid_dpop_proof"

    accepted = client.post("/v1/auth/token", data=form, headers={
        "DPoP": dpop.sign_proof(key, "POST", "https://sc.example/v1/auth/token")})
    assert accepted.status_code == 200


def test_the_real_client_logs_in_reads_me_and_rotates_its_key(live_server):
    from siliconcompiler.remote import Client, Credentials

    credentials = Credentials("sc-home/auth/remote.json")
    credentials.set_server(live_server)
    client = Client(credentials)

    user = client.me()
    assert user["issuer"] == "local"
    old, = [device["id"] for device in client.devices() if device["current"]]

    client.rotate_key()

    again = Client(Credentials("sc-home/auth/remote.json"))
    assert again.me()["id"] == user["id"]
    new, = [device["id"] for device in again.devices() if device["current"]]
    assert new != old
