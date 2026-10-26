'''
DPoP (RFC 9449), shared by client (signing) and server (verifying).

Where nothing verifies identity, the session's bound key is the only control,
so the thumbprint must be computed identically at both ends: hence one module.
'''

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


# Pinned at both ends, never read from the attacker-controlled `alg` header.
ALGORITHM = "ES256"

# How far out of step a proof's `iat` may be: ordinary drift, not replay.
PROOF_LIFETIME_SECONDS = 60


class DPoPError(Exception):
    '''A proof that does not hold up: `invalid-dpop-proof`, failed, never refreshed.'''


def generate_key():
    '''A new P-256 private key, generated locally and never sent anywhere.'''
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
    '''The public half as a JWK: ``kty``, ``crv``, ``x`` and ``y``.

    From the PUBLIC key, always: PyJWT adds ``d`` for a private one.
    '''
    from jwt.algorithms import ECAlgorithm

    public = key.public_key() if hasattr(key, "public_key") else key
    return ECAlgorithm.to_jwk(public, as_dict=True)


def jwk_thumbprint(jwk: Dict[str, Any]) -> str:
    '''The RFC 7638 thumbprint of a JWK, the `jkt`: required members only,
    sorted, no whitespace, or the two ends disagree.'''
    from jwt.utils import base64url_encode

    try:
        required = {"crv": jwk["crv"], "kty": jwk["kty"],
                    "x": jwk["x"], "y": jwk["y"]}
    except KeyError as e:
        raise DPoPError(f"JWK is missing {e.args[0]}") from None

    canonical = json.dumps(required, separators=(",", ":"), sort_keys=True)
    return base64url_encode(hashlib.sha256(canonical.encode("ascii")).digest()).decode()


def access_token_hash(access_token: str) -> str:
    '''`ath`: the access token's hash, binding a proof to that token.'''
    from jwt.utils import base64url_encode

    return base64url_encode(hashlib.sha256(access_token.encode("ascii")).digest()).decode()


def sign_proof(key, method: str, url: str,
               access_token: Optional[str] = None,
               nonce: Optional[str] = None,
               iat: Optional[int] = None) -> str:
    '''One proof for one request, client side. ``iat`` overrides the time, for
    a caller correcting its clock by the server's.'''
    import jwt

    claims: Dict[str, Any] = {
        "jti": str(uuid.uuid4()),
        "htm": method.upper(),
        "htu": _htu(url),
        "iat": int(time.time()) if iat is None else int(iat),
    }
    if access_token is not None:
        claims["ath"] = access_token_hash(access_token)
    if nonce is not None:
        claims["nonce"] = nonce

    return jwt.encode(
        claims, key, algorithm=ALGORITHM,
        headers={"typ": "dpop+jwt", "jwk": public_jwk(key)})


# The port a scheme implies, omitted from a canonical `htu`.
_DEFAULT_PORTS = {"http": "80", "https": "443"}


def _htu(url: str) -> str:
    '''Canonical `htu` (identity *The proof rules*): scheme and host lowercased,
    default port and query dropped, the path as sent.'''
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host, port = parts.netloc.rpartition("@")[2].lower(), ""
    # An IPv6 literal keeps its brackets, and its colons are not a port's.
    if ":" in host and not host.endswith("]"):
        host, _, port = host.rpartition(":")
    if port == _DEFAULT_PORTS.get(scheme):
        port = ""
    return f"{scheme}://{host}{':' + port if port else ''}{parts.path}"


def verify_proof(proof: str, method: str, url: str,
                 access_token: Optional[str] = None,
                 now: Optional[int] = None) -> str:
    '''Check a proof, server side, and return its thumbprint.

    The caller checks `jti` replay and compares the thumbprint with the bound key.
    '''
    import jwt

    try:
        header = jwt.get_unverified_header(proof)
    except jwt.PyJWTError as e:
        raise DPoPError(f"proof is not a JWT: {e}") from None

    if header.get("typ") != "dpop+jwt":
        raise DPoPError("proof is missing typ=dpop+jwt")

    # Before any key is built: `none` or a symmetric `alg` is refused.
    if header.get("alg") != ALGORITHM:
        raise DPoPError(f"proof must be signed with {ALGORITHM}")

    jwk = header.get("jwk")
    if not isinstance(jwk, dict):
        raise DPoPError("proof is missing its jwk header")
    if "d" in jwk:
        raise DPoPError("proof carries a private key")

    thumbprint = jwk_thumbprint(jwk)

    try:
        key = jwt.PyJWK.from_dict({**jwk, "alg": ALGORITHM}).key
        claims = jwt.decode(proof, key, algorithms=[ALGORITHM],
                            # The window below is the only `iat` check: PyJWT's
                            # refuses a client a second fast.
                            options={"verify_exp": False, "verify_iat": False,
                                     "require": ["jti", "htm", "htu", "iat"]})
    except jwt.PyJWTError as e:
        raise DPoPError(f"proof does not verify: {e}") from None

    if not isinstance(claims["htm"], str) or claims["htm"].upper() != method.upper():
        raise DPoPError("proof htm does not match the request method")
    # Both sides canonical, so `:443` or a mixed-case host still matches.
    if not isinstance(claims["htu"], str) or _htu(claims["htu"]) != _htu(url):
        raise DPoPError("proof htu does not match the request URI")

    issued = claims["iat"]
    current = int(time.time()) if now is None else now
    if not isinstance(issued, int):
        raise DPoPError("proof iat is not a number")
    if abs(current - issued) > PROOF_LIFETIME_SECONDS:
        raise DPoPError("proof iat is outside the acceptable window")

    if access_token is not None:
        if claims.get("ath") != access_token_hash(access_token):
            raise DPoPError("proof ath does not match the access token")

    return thumbprint
