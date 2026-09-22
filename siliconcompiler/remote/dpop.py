'''
DPoP -- RFC 9449 -- shared by both halves of the remote path.

Nothing verifies who a caller is in this deployment, so the key a session is
bound to is the only real control the mode has: it is what stops user A on a
shared machine presenting user B's derivation and getting a session as B. That
makes the thumbprint the one value client and server must compute identically,
which is why the computation lives in one module rather than twice.

The client signs a proof per request; the server verifies it. Both directions
are here, and only the direction a process needs is ever called.
'''

import base64
import hashlib
import json
import time
import uuid

from typing import Any, Dict, Optional

__all__ = [
    "ALGORITHM", "DPoPError",
    "generate_key", "load_key", "public_jwk", "jwk_thumbprint",
    "sign_proof", "verify_proof", "access_token_hash",
]


# ES256 and nothing else. The algorithm is pinned at both ends rather than read
# from the proof's header: `alg` is attacker-controlled input, and accepting
# whatever it names is the classic JWS defect.
ALGORITHM = "ES256"

# How far out of step a proof's `iat` may be. RFC 9449 leaves the window to the
# server; this is wide enough for ordinary clock drift and far short of making a
# captured proof useful.
PROOF_LIFETIME_SECONDS = 60


class DPoPError(Exception):
    '''A proof that does not hold up.

    Every instance of this is `invalid-dpop-proof` on the wire, and the client's
    answer to it is to fail rather than to refresh: a bad proof is not a stale
    token.
    '''


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_key():
    '''A new P-256 private key.

    Generated locally and never sent anywhere. An operator handing a user a key
    pair is refused outright: the private half staying private is the single
    property DPoP has.
    '''
    from cryptography.hazmat.primitives.asymmetric import ec

    return ec.generate_private_key(ec.SECP256R1())


def serialize_key(key) -> bytes:
    '''PEM for the private key, to be written 0600 and no wider.'''
    from cryptography.hazmat.primitives import serialization

    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())


def load_key(pem: bytes):
    '''Read a private key back.'''
    from cryptography.hazmat.primitives import serialization

    return serialization.load_pem_private_key(pem, password=None)


def public_jwk(key) -> Dict[str, str]:
    '''The public half, as a JWK.

    Built from the curve point rather than through a library's JWK exporter so
    that the member set is exactly the four RFC 7638 requires for a thumbprint,
    in the order they are hashed.
    '''
    public = key.public_key() if hasattr(key, "public_key") else key
    numbers = public.public_numbers()

    size = (public.curve.key_size + 7) // 8

    return {
        "crv": "P-256",
        "kty": "EC",
        "x": _b64url(numbers.x.to_bytes(size, "big")),
        "y": _b64url(numbers.y.to_bytes(size, "big")),
    }


def jwk_thumbprint(jwk: Dict[str, Any]) -> str:
    '''The RFC 7638 thumbprint of a JWK: this is the `jkt`.

    The required members only, lexicographically ordered, no whitespace. Any
    other spelling produces a different thumbprint, which would bind a session
    to a key the other half cannot recognise.
    '''
    try:
        required = {"crv": jwk["crv"], "kty": jwk["kty"],
                    "x": jwk["x"], "y": jwk["y"]}
    except KeyError as e:
        raise DPoPError(f"JWK is missing {e.args[0]}") from None

    canonical = json.dumps(required, separators=(",", ":"), sort_keys=True)
    return _b64url(hashlib.sha256(canonical.encode("ascii")).digest())


def access_token_hash(access_token: str) -> str:
    '''`ath`: the hash of the access token this proof is presented with.

    It is what stops a proof captured on one request being replayed against a
    different token.
    '''
    return _b64url(hashlib.sha256(access_token.encode("ascii")).digest())


def sign_proof(key, method: str, url: str,
               access_token: Optional[str] = None,
               nonce: Optional[str] = None) -> str:
    '''One proof, for one request. Client side.

    `htu` is the request URI with any query and fragment removed, per RFC 9449;
    `htm` is the method. A proof is good for one request and is not reused.
    '''
    import jwt

    claims: Dict[str, Any] = {
        "jti": str(uuid.uuid4()),
        "htm": method.upper(),
        "htu": _htu(url),
        "iat": int(time.time()),
    }
    if access_token is not None:
        claims["ath"] = access_token_hash(access_token)
    if nonce is not None:
        # The server asked for one with `use_dpop_nonce`; the client retries the
        # same request carrying it. A client that only refreshes on 401 loops
        # forever here, which is why this is not optional to implement.
        claims["nonce"] = nonce

    return jwt.encode(
        claims, key, algorithm=ALGORITHM,
        headers={"typ": "dpop+jwt", "jwk": public_jwk(key)})


def _htu(url: str) -> str:
    '''The `htu` value: scheme, authority and path, with query and fragment
    removed rather than normalised away.'''
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def verify_proof(proof: str, method: str, url: str,
                 access_token: Optional[str] = None,
                 expected_jkt: Optional[str] = None,
                 nonce: Optional[str] = None,
                 now: Optional[int] = None) -> str:
    '''Check a proof and return the thumbprint it was signed with. Server side.

    Raises :class:`DPoPError` for every way a proof can fail to hold up, which
    the handler renders as `invalid-dpop-proof`. Replay is the caller's problem:
    this returns the `jti` check's input rather than remembering anything.
    '''
    import jwt

    try:
        header = jwt.get_unverified_header(proof)
    except jwt.PyJWTError as e:
        raise DPoPError(f"proof is not a JWT: {e}") from None

    if header.get("typ") != "dpop+jwt":
        raise DPoPError("proof is missing typ=dpop+jwt")

    # The algorithm is pinned rather than read from the header, so a proof
    # naming `none` or a symmetric algorithm is refused before any key is built
    # from attacker-supplied material.
    if header.get("alg") != ALGORITHM:
        raise DPoPError(f"proof must be signed with {ALGORITHM}")

    jwk = header.get("jwk")
    if not isinstance(jwk, dict):
        raise DPoPError("proof is missing its jwk header")
    if "d" in jwk:
        # A private key in a header is either a serious client defect or an
        # attempt to have the server sign something; either way it is not a
        # proof.
        raise DPoPError("proof carries a private key")

    thumbprint = jwk_thumbprint(jwk)

    try:
        key = jwt.PyJWK.from_dict({**jwk, "alg": ALGORITHM}).key
        claims = jwt.decode(proof, key, algorithms=[ALGORITHM],
                            options={"verify_exp": False,
                                     "require": ["jti", "htm", "htu", "iat"]})
    except jwt.PyJWTError as e:
        raise DPoPError(f"proof does not verify: {e}") from None

    if claims["htm"].upper() != method.upper():
        raise DPoPError("proof htm does not match the request method")
    if claims["htu"] != _htu(url):
        raise DPoPError("proof htu does not match the request URI")

    issued = claims["iat"]
    current = int(time.time()) if now is None else now
    if not isinstance(issued, int):
        raise DPoPError("proof iat is not a number")
    if abs(current - issued) > PROOF_LIFETIME_SECONDS:
        raise DPoPError("proof iat is outside the acceptable window")

    if nonce is not None and claims.get("nonce") != nonce:
        raise DPoPError("proof carries the wrong nonce")

    if access_token is not None:
        if claims.get("ath") != access_token_hash(access_token):
            raise DPoPError("proof ath does not match the access token")

    if expected_jkt is not None and thumbprint != expected_jkt:
        # The bound key and the presenting key differ. On the token endpoint
        # this is the first-contact binding refusing an impostor; on an ordinary
        # request it is a token being presented by something that does not hold
        # its key.
        raise DPoPError("proof key does not match the bound key")

    return thumbprint
