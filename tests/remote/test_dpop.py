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


def proof_with_htu(key, method, htu, access_token=None):
    '''A proof carrying ``htu`` exactly as given, as a client that does not
    canonicalise would sign it.'''
    import uuid

    import jwt

    claims = {"jti": str(uuid.uuid4()), "htm": method, "htu": htu, "iat": int(time.time())}
    if access_token is not None:
        claims["ath"] = dpop.access_token_hash(access_token)
    return jwt.encode(claims, key, algorithm=dpop.ALGORITHM,
                      headers={"typ": "dpop+jwt", "jwk": dpop.public_jwk(key)})


@pytest.mark.parametrize("signed", ["https://SC-SERVER.test:443/v1/jobs",
                                    "HTTPS://Sc-Server.Test/v1/jobs",
                                    "https://sc-server.test:443/v1/jobs?x=1"])
def test_htu_is_compared_canonical_on_both_sides(key, signed):
    '''Identity *The proof rules*: scheme and host lowercased and a default
    port omitted, on the proof's side and on the server's, so `:443` or a
    mixed-case host is accepted.'''
    dpop.verify_proof(proof_with_htu(key, "GET", signed), "GET", URL)
    dpop.verify_proof(proof_with_htu(key, "GET", URL), "GET", signed)


@pytest.mark.parametrize("other", ["https://sc-server.test:8443/v1/jobs",
                                   "http://sc-server.test/v1/jobs",
                                   "https://sc-server.test/v1/Jobs"])
def test_canonical_is_not_lax(key, other):
    '''Another port, another scheme or another path is another URI: the
    path is compared as sent.'''
    with pytest.raises(dpop.DPoPError, match="htu"):
        dpop.verify_proof(proof_with_htu(key, "GET", other), "GET", URL)


def test_the_client_signs_the_canonical_form(key):
    import jwt

    proof = dpop.sign_proof(key, "GET", "https://SC-SERVER.test:443/v1/jobs?state=running")

    assert jwt.decode(proof, options={"verify_signature": False})["htu"] == URL


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


@pytest.mark.parametrize("ahead,accepted", [(2, True), (dpop.PROOF_LIFETIME_SECONDS - 5, True),
                                            (dpop.PROOF_LIFETIME_SECONDS + 5, False)])
def test_a_proof_signed_by_a_clock_ahead_is_held_to_the_same_window(key, ahead, accepted):
    '''🔴 Signed ahead, not merely checked behind: a client whose clock runs a
    few seconds fast is inside the window, and was once refused by the JWT
    library's own `iat` check before the window was ever asked.'''
    proof = dpop.sign_proof(key, "GET", URL, iat=int(time.time()) + ahead)

    if accepted:
        dpop.verify_proof(proof, "GET", URL)
    else:
        with pytest.raises(dpop.DPoPError, match="window"):
            dpop.verify_proof(proof, "GET", URL)


@pytest.mark.parametrize("claim", ["htm", "htu"])
def test_a_claim_that_is_not_a_string_is_refused_not_a_crash(key, claim):
    '''A signed proof is still the caller's input: a number where a string
    belongs is a refused proof, never an exception the server answers 500.'''
    import jwt

    claims = {"jti": "x", "htm": "GET", "htu": URL, "iat": int(time.time())}
    claims[claim] = 7
    proof = jwt.encode(claims, key, algorithm="ES256",
                       headers={"typ": "dpop+jwt", "jwk": dpop.public_jwk(key)})

    with pytest.raises(dpop.DPoPError, match=claim):
        dpop.verify_proof(proof, "GET", URL)


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
