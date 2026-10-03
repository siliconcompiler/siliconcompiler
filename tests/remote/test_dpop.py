import json
import time

import jwt
import pytest

from siliconcompiler.remote import dpop


URL = "https://sc-server.test/v1/jobs"


@pytest.fixture
def key():
    return dpop.generate_key()


def _thumbprint(key):
    return dpop.jwk_thumbprint(dpop.public_jwk(key))


def test_a_key_round_trips_through_pem_and_two_keys_are_two_machines(key):
    '''A different thumbprint is a different machine.'''
    again = dpop.load_key(dpop.serialize_key(key))

    assert _thumbprint(again) == _thumbprint(key)
    assert _thumbprint(dpop.generate_key()) != _thumbprint(key)


def test_a_thumbprint_is_the_rfc_7638_construction(key):
    '''The required members only -- an extra one would later be removed and
    change every thumbprint -- sorted, no whitespace, SHA-256, base64url
    unpadded: client and server must agree exactly.'''
    import base64
    import hashlib

    jwk = dpop.public_jwk(key)
    assert set(jwk) == {"crv", "kty", "x", "y"}

    canonical = json.dumps(jwk, separators=(",", ":"), sort_keys=True)
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(canonical.encode()).digest()).rstrip(b"=").decode()

    assert dpop.jwk_thumbprint(jwk) == expected
    assert len(expected) == 43       # 256 bits, unpadded


def test_a_jwk_missing_a_member_names_it():
    with pytest.raises(dpop.DPoPError, match="crv"):
        dpop.jwk_thumbprint({"kty": "EC", "x": "a", "y": "b"})


def test_a_proof_verifies_and_returns_its_thumbprint(key):
    proof = dpop.sign_proof(key, "POST", URL)

    assert dpop.verify_proof(proof, "POST", URL) == _thumbprint(key)


def test_htu_drops_the_query_and_fragment(key):
    '''RFC 9449: valid for the same path with other filters, not another path.'''
    proof = dpop.sign_proof(key, "GET", f"{URL}?state=running#top")

    dpop.verify_proof(proof, "GET", URL)

    with pytest.raises(dpop.DPoPError, match="htu"):
        dpop.verify_proof(proof, "GET", "https://sc-server.test/v1/me")


def proof_with_htu(key, method, htu, access_token=None):
    '''A proof carrying ``htu`` exactly as given, as a client that does not
    canonicalise would sign it.'''
    import uuid

    claims = {"jti": str(uuid.uuid4()), "htm": method, "htu": htu, "iat": int(time.time())}
    if access_token is not None:
        claims["ath"] = dpop.access_token_hash(access_token)
    return jwt.encode(claims, key, algorithm=dpop.ALGORITHM,
                      headers={"typ": "dpop+jwt", "jwk": dpop.public_jwk(key)})


@pytest.mark.parametrize("signed", ["https://SC-SERVER.test:443/v1/jobs",
                                    "HTTPS://Sc-Server.Test/v1/jobs",
                                    "https://sc-server.test:443/v1/jobs?x=1"])
def test_htu_is_compared_canonical_on_both_sides(key, signed):
    '''Scheme and host lowercased and a default port omitted, on both sides.'''
    dpop.verify_proof(proof_with_htu(key, "GET", signed), "GET", URL)
    dpop.verify_proof(proof_with_htu(key, "GET", URL), "GET", signed)


@pytest.mark.parametrize("other", ["https://sc-server.test:8443/v1/jobs",
                                   "http://sc-server.test/v1/jobs",
                                   "https://sc-server.test/v1/Jobs"])
def test_canonical_is_not_lax(key, other):
    '''Another port, scheme or path is another URI; the path is as sent.'''
    with pytest.raises(dpop.DPoPError, match="htu"):
        dpop.verify_proof(proof_with_htu(key, "GET", other), "GET", URL)


def test_the_client_signs_the_canonical_form(key):
    proof = dpop.sign_proof(key, "GET", "https://SC-SERVER.test:443/v1/jobs?state=running")

    assert jwt.decode(proof, options={"verify_signature": False})["htu"] == URL


def test_a_proof_is_bound_to_its_method_and_its_access_token(key):
    '''`ath` stops a captured proof being replayed against another token.'''
    with pytest.raises(dpop.DPoPError, match="htm"):
        dpop.verify_proof(dpop.sign_proof(key, "POST", URL), "DELETE", URL)

    proof = dpop.sign_proof(key, "GET", URL, access_token="token-one")
    dpop.verify_proof(proof, "GET", URL, access_token="token-one")
    with pytest.raises(dpop.DPoPError, match="ath"):
        dpop.verify_proof(proof, "GET", URL, access_token="token-two")


@pytest.mark.parametrize("sign", [1, -1], ids=["stale", "future"])
def test_a_proof_outside_the_window_is_refused(key, sign):
    '''Absolute, not one-sided: a clock far ahead is as wrong as one behind.'''
    proof = dpop.sign_proof(key, "GET", URL)

    with pytest.raises(dpop.DPoPError, match="iat"):
        dpop.verify_proof(proof, "GET", URL,
                          now=int(time.time()) + sign * (dpop.PROOF_LIFETIME_SECONDS + 5))


@pytest.mark.parametrize("ahead,accepted", [(2, True), (dpop.PROOF_LIFETIME_SECONDS - 5, True),
                                            (dpop.PROOF_LIFETIME_SECONDS + 5, False)])
def test_a_proof_signed_by_a_clock_ahead_is_held_to_the_same_window(key, ahead, accepted):
    '''🔴 A client a few seconds fast is inside the window; the JWT library's
    own `iat` check once refused it first.'''
    proof = dpop.sign_proof(key, "GET", URL, iat=int(time.time()) + ahead)

    if accepted:
        dpop.verify_proof(proof, "GET", URL)
    else:
        with pytest.raises(dpop.DPoPError, match="window"):
            dpop.verify_proof(proof, "GET", URL)


def _forged(key, claims=None, typ="dpop+jwt", jwk=None, signer="same", algorithm="ES256"):
    signed_with = {"same": key, "other": dpop.generate_key(), "none": None}[signer]
    return jwt.encode({"jti": "x", "htm": "GET", "htu": URL, "iat": int(time.time()),
                       **(claims or {})},
                      signed_with, algorithm=algorithm,
                      headers={"typ": typ, "jwk": jwk or dpop.public_jwk(key)})


@pytest.mark.parametrize("forge,said", [
    # `alg` is attacker input: `none` is the classic JWS defect.
    (dict(signer="none", algorithm="none"), "ES256"),
    (dict(typ="JWT"), "typ"),
    # A client defect, or an attempt to have the server sign something.
    (dict(jwk="private"), "private key"),
    # The header's jwk is the thumbprint: else anyone claims any thumbprint.
    (dict(signer="other"), "does not verify"),
    # Still the caller's input: refused, never a 500.
    (dict(claims={"htm": 7}), "htm"),
    (dict(claims={"htu": 7}), "htu"),
], ids=["alg-none", "typ", "private-key", "other-signer", "htm-not-a-string",
        "htu-not-a-string"])
def test_a_forged_proof_is_refused(key, forge, said):
    if forge.get("jwk") == "private":
        forge = dict(jwk={**dpop.public_jwk(key), "d": "definitely-not-public"})

    with pytest.raises(dpop.DPoPError, match=said):
        dpop.verify_proof(_forged(key, **forge), "GET", URL)


def test_garbage_is_refused_rather_than_raising_something_else():
    with pytest.raises(dpop.DPoPError):
        dpop.verify_proof("not-a-jwt-at-all", "GET", URL)
