import json
import time

import pytest

from siliconcompiler.remote import dpop


URL = "https://sc-server.test/v1/jobs"


@pytest.fixture
def key():
    return dpop.generate_key()


###########################
# Keys and thumbprints
###########################

def test_a_key_round_trips_through_pem(key):
    '''The key is written to disk between commands, so it has to come back as
    the same key -- a different thumbprint is a different machine.'''
    again = dpop.load_key(dpop.serialize_key(key))

    assert dpop.jwk_thumbprint(dpop.public_jwk(again)) == \
        dpop.jwk_thumbprint(dpop.public_jwk(key))


def test_the_public_jwk_carries_only_what_a_thumbprint_hashes(key):
    '''RFC 7638 hashes the required members and nothing else, so any extra
    member here would be a member somebody later removes and changes every
    thumbprint on every deployment.'''
    assert set(dpop.public_jwk(key)) == {"crv", "kty", "x", "y"}


def test_a_thumbprint_is_the_rfc_7638_construction(key):
    '''Computed here rather than trusted, because client and server must agree
    exactly: the members sorted, no whitespace, SHA-256, base64url unpadded.'''
    import base64
    import hashlib

    jwk = dpop.public_jwk(key)
    canonical = json.dumps(
        {"crv": jwk["crv"], "kty": jwk["kty"], "x": jwk["x"], "y": jwk["y"]},
        separators=(",", ":"), sort_keys=True)
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(canonical.encode()).digest()).rstrip(b"=").decode()

    assert dpop.jwk_thumbprint(jwk) == expected
    assert len(dpop.jwk_thumbprint(jwk)) == 43       # 256 bits, unpadded


def test_two_keys_are_two_machines():
    assert dpop.jwk_thumbprint(dpop.public_jwk(dpop.generate_key())) != \
        dpop.jwk_thumbprint(dpop.public_jwk(dpop.generate_key()))


###########################
# Signing and verifying
###########################

def test_a_proof_verifies_and_returns_its_thumbprint(key):
    proof = dpop.sign_proof(key, "POST", URL)

    assert dpop.verify_proof(proof, "POST", URL) == \
        dpop.jwk_thumbprint(dpop.public_jwk(key))


def test_htu_drops_the_query_and_fragment(key):
    '''RFC 9449 compares the URI without them, so a proof signed for a filtered
    listing is valid for the same path with different filters -- and one signed
    for a different path is not.'''
    proof = dpop.sign_proof(key, "GET", f"{URL}?state=running#top")

    dpop.verify_proof(proof, "GET", URL)

    with pytest.raises(dpop.DPoPError, match="htu"):
        dpop.verify_proof(proof, "GET", "https://sc-server.test/v1/me")


def test_a_proof_is_bound_to_its_method(key):
    proof = dpop.sign_proof(key, "POST", URL)

    with pytest.raises(dpop.DPoPError, match="htm"):
        dpop.verify_proof(proof, "DELETE", URL)


def test_a_proof_is_bound_to_its_access_token(key):
    '''`ath` is what stops a proof captured on one request being replayed
    against a different token.'''
    proof = dpop.sign_proof(key, "GET", URL, access_token="token-one")

    dpop.verify_proof(proof, "GET", URL, access_token="token-one")

    with pytest.raises(dpop.DPoPError, match="ath"):
        dpop.verify_proof(proof, "GET", URL, access_token="token-two")


def test_a_stale_proof_is_refused(key):
    proof = dpop.sign_proof(key, "GET", URL)

    with pytest.raises(dpop.DPoPError, match="iat"):
        dpop.verify_proof(proof, "GET", URL,
                          now=int(time.time()) + dpop.PROOF_LIFETIME_SECONDS + 5)


def test_a_proof_from_the_future_is_refused(key):
    '''The window is absolute, not one-sided: a clock far ahead is as much a
    sign of something wrong as one far behind.'''
    proof = dpop.sign_proof(key, "GET", URL)

    with pytest.raises(dpop.DPoPError, match="iat"):
        dpop.verify_proof(proof, "GET", URL,
                          now=int(time.time()) - dpop.PROOF_LIFETIME_SECONDS - 5)


def test_the_wrong_key_is_refused(key):
    '''What the first-contact binding is made of: the presented key must be the
    bound one.'''
    proof = dpop.sign_proof(dpop.generate_key(), "GET", URL)
    bound = dpop.jwk_thumbprint(dpop.public_jwk(key))

    with pytest.raises(dpop.DPoPError, match="does not match the bound key"):
        dpop.verify_proof(proof, "GET", URL, expected_jkt=bound)


###########################
# Things that are not proofs
###########################

def test_the_algorithm_is_pinned_not_read_from_the_header(key):
    '''`alg` is attacker-controlled input. Accepting whatever it names is the
    classic JWS defect, and `none` is the classic instance of it.'''
    import jwt

    forged = jwt.encode({"jti": "x", "htm": "GET", "htu": URL,
                         "iat": int(time.time())},
                        key=None, algorithm="none",
                        headers={"typ": "dpop+jwt", "jwk": dpop.public_jwk(key)})

    with pytest.raises(dpop.DPoPError, match="ES256"):
        dpop.verify_proof(forged, "GET", URL)


def test_a_proof_without_the_dpop_type_is_refused(key):
    import jwt

    wrong = jwt.encode({"jti": "x", "htm": "GET", "htu": URL,
                        "iat": int(time.time())},
                       key, algorithm="ES256",
                       headers={"typ": "JWT", "jwk": dpop.public_jwk(key)})

    with pytest.raises(dpop.DPoPError, match="typ"):
        dpop.verify_proof(wrong, "GET", URL)


def test_a_proof_carrying_a_private_key_is_refused(key):
    '''Either a serious client defect or an attempt to have the server sign
    something. Neither is a proof.'''
    import jwt

    jwk = dict(dpop.public_jwk(key))
    jwk["d"] = "definitely-not-public"

    smuggled = jwt.encode({"jti": "x", "htm": "GET", "htu": URL,
                           "iat": int(time.time())},
                          key, algorithm="ES256",
                          headers={"typ": "dpop+jwt", "jwk": jwk})

    with pytest.raises(dpop.DPoPError, match="private key"):
        dpop.verify_proof(smuggled, "GET", URL)


def test_a_proof_signed_by_a_key_other_than_its_jwk_is_refused(key):
    '''The header's jwk is what the thumbprint is taken from, so a proof whose
    signature does not come from it would let anyone claim any thumbprint.'''
    import jwt

    claimed = dpop.public_jwk(key)
    signed_with = dpop.generate_key()

    forged = jwt.encode({"jti": "x", "htm": "GET", "htu": URL,
                         "iat": int(time.time())},
                        signed_with, algorithm="ES256",
                        headers={"typ": "dpop+jwt", "jwk": claimed})

    with pytest.raises(dpop.DPoPError, match="does not verify"):
        dpop.verify_proof(forged, "GET", URL)


def test_garbage_is_refused_rather_than_raising_something_else():
    with pytest.raises(dpop.DPoPError):
        dpop.verify_proof("not-a-jwt-at-all", "GET", URL)


def test_a_jwk_missing_a_member_names_it():
    with pytest.raises(dpop.DPoPError, match="crv"):
        dpop.jwk_thumbprint({"kty": "EC", "x": "a", "y": "b"})


###########################
# Nonces
###########################

def test_a_nonce_round_trips(key):
    '''The server challenges with `use_dpop_nonce`; the client re-sends the
    same request carrying the nonce. A client that only refreshes on 401 loops
    here forever, which is why this is not optional.'''
    proof = dpop.sign_proof(key, "GET", URL, nonce="server-said-this")

    dpop.verify_proof(proof, "GET", URL, nonce="server-said-this")

    with pytest.raises(dpop.DPoPError, match="nonce"):
        dpop.verify_proof(proof, "GET", URL, nonce="a-different-nonce")
