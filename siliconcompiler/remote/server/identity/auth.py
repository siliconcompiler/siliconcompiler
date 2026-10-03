'''
Sessions: minting them, presenting them, and ending them.

Nothing here verifies who a caller is: identity is self-asserted namespacing,
which buys ownership, not a boundary. The one real control is the key: the
first `client_credentials` issuance for a subject records its thumbprint, and a
different key is refused thereafter, so once B has used the server, A cannot
become B.
'''

import logging
import os
import secrets
import threading
import time
import uuid

from pathlib import Path
from typing import Dict, Optional

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import OAuthError, ProblemError
from siliconcompiler.remote.server.state.store import Store, now, parse, stamp

__all__ = [
    "SCOPES", "expand_scope", "TokenIssuer", "Session",
    "ACCESS_TOKEN_SECONDS", "REFRESH_TOKEN_SECONDS", "SESSION_SECONDS",
]


logger = logging.getLogger("sc-server")


# The registered scopes (identity.md, *Scopes*); none is ever administrative.
SCOPES = (
    "jobs:read",
    "jobs:write",
    "jobs:delete",
    "artifacts:read",
    "devices:read",
    "devices:write",
    "profile:read",
)

# Expanded at mint, not at check, so the stored and published scope agree.
_IMPLIES = {
    "jobs:write": "jobs:read",
    "jobs:delete": "jobs:read",
    "devices:write": "devices:read",
}

ACCESS_TOKEN_SECONDS = 900          # 15 minutes
REFRESH_TOKEN_SECONDS = 604800      # 7 days, sliding
SESSION_SECONDS = 1036800           # 12 days, the family cap. NEVER extended

# A replaced refresh token repeated within this, with the family's key, gets
# the replacement already issued. Minutes, since a lost response's retry comes
# at least one client timeout later.
REFRESH_GRACE_SECONDS = 300

# The column records WHY a family ended, for an operator; the wire says WHAT
# THE CLIENT MUST DO, one branch per value.
_WIRE_REASON = {
    "user_logout": "revoked",
    "reuse_detected": "reused",
    "device_revoked": "revoked",
    "ci_credential_revoked": "revoked",
    "admin": "revoked",
    "account_inactive": "deactivated",
}

_SIGNING_KEY_FILE = "token-signing-key"


def expand_scope(requested: Optional[str]) -> str:
    '''The scope a token is minted with: every registered scope where none is
    asked for; unrecognised values dropped, `invalid_scope` if nothing is left.
    '''
    if requested is None or not requested.strip():
        granted = set(SCOPES)
    else:
        granted = set(requested.split()) & set(SCOPES)
        if not granted:
            raise OAuthError("invalid_scope",
                             "no requested scope is one this server registers")

    for write, read in _IMPLIES.items():
        if write in granted:
            granted.add(read)

    # In the vocabulary's order, so equal scopes are equal strings.
    return " ".join(scope for scope in SCOPES if scope in granted)


class _KeyMismatch(Exception):
    """A known subject presented a key that is not the one it is bound to."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(device_id)


class Session:
    '''A verified caller, for the duration of one request.'''

    def __init__(self, user_id: str, scope: str, family_id: str,
                 device_id: Optional[str], jkt: str, expires_at: Optional[float] = None):
        self.user_id = user_id
        self.scope = frozenset(scope.split())
        self.family_id = family_id
        self.device_id = device_id
        self.jkt = jkt
        # When this request's credential expires; a stream it opens ends by then.
        self.expires_at = expires_at

    def require(self, scope: str) -> None:
        '''Refuse unless the token covers this endpoint; a refresh re-mints the
        same ceiling, so the client fails rather than retrying.'''
        if scope not in self.scope:
            raise ProblemError(
                "insufficient-scope",
                detail=f"this endpoint needs {scope}",
                headers={"WWW-Authenticate":
                         f'DPoP error="insufficient_scope", scope="{scope}"'})


class TokenIssuer:
    '''Mints and checks this deployment's tokens, symmetrically signed: one
    process both issues and verifies.'''

    def __init__(self, datadir: Path, store: Store, bind_keys: bool = True):
        self._store = store
        self._secret = _load_or_create_secret(Path(datadir) / _SIGNING_KEY_FILE)

        # ON by default; off declares a single trust domain, which a container
        # fleet needs (every container derives the same subject). Off by default
        # would fail silently: one user reading another's designs.
        self._bind_keys = bind_keys

        # Seen proof ids, held for the proof window; older fails on `iat`.
        self._seen: Dict[str, float] = {}
        # 🔴 Requests run on threads of their own, so the check that a `jti`
        # is new and the write that makes it seen are one step.
        self._seen_lock = threading.Lock()

    @property
    def secret(self) -> bytes:
        '''The deployment's one signing secret. Every other signer derives its
        own key from it, so no signature passes for another purpose.'''
        return self._secret

    ######################################################################
    # Minting
    ######################################################################

    def client_credentials(self, subject: str, jkt: str,
                           requested_scope: Optional[str],
                           machine_id_hash: Optional[str] = None,
                           machine_id_source: str = "none",
                           display_name: Optional[str] = None) -> dict:
        '''Log in with no browser, no issuer and no human: RFC 6749's shape, but
        the client secret is nominal.'''
        try:
            with self._store.transaction():
                user = self._store.upsert_user(
                    "local", subject,
                    posix_account=subject,
                    display_name=display_name)

                if user["deactivated_at"] is not None:
                    raise OAuthError("invalid_grant", "this account is not active",
                                     reason="deactivated")

                device = self._bind_device(user["id"], jkt, machine_id_hash,
                                           machine_id_source, display_name)
                return self._issue(user["id"], device["id"], jkt,
                                   expand_scope(requested_scope))
        except _KeyMismatch as mismatch:
            # Recorded AFTER the rollback, deliberately: inside the aborted
            # transaction the one event worth keeping would be lost.
            self._store.execute(
                "INSERT INTO device_events (device_id, kind) "
                "VALUES (?, 'reauth_failed')", (mismatch.device_id,))
            logger.warning(
                f"refused a session for a known subject presenting a different "
                f"key (device {mismatch.device_id})")
            raise OAuthError(
                "invalid_client",
                "this subject is bound to a different key; retrying will not "
                "help, and an operator can release the binding",
                status=401) from None

    def _bind_device(self, user_id: str, jkt: str,
                     machine_id_hash: Optional[str],
                     machine_id_source: str,
                     display_name: Optional[str]):
        '''First contact records the key; later contact must present it.
        Otherwise anyone could present B's public derivation with their own key.
        '''
        existing = self._store.one(
            "SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL",
            (user_id,))

        if existing is None:
            self._retire_elsewhere(user_id, jkt)

            device_id = str(uuid.uuid4())
            self._store.execute(
                "INSERT INTO devices "
                "(id, user_id, name, dpop_jkt, machine_id_hash, "
                " machine_id_source, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (device_id, user_id, display_name or "this machine", jkt,
                 machine_id_hash, machine_id_source, now()))
            self._store.execute(
                "INSERT INTO device_events (device_id, kind) VALUES (?, 'enrolled')",
                (device_id,))
            return self._store.one("SELECT * FROM devices WHERE id = ?", (device_id,))

        if existing["dpop_jkt"] != jkt:
            if self._bind_keys:
                # Raised, so the caller records it after the rollback.
                raise _KeyMismatch(existing["id"])

            # Binding off: one trust domain, so the newest key wins.
            self._store.execute(
                "UPDATE devices SET dpop_jkt = ?, last_seen_at = ? WHERE id = ?",
                (jkt, now(), existing["id"]))
            return self._store.one(
                "SELECT * FROM devices WHERE id = ?", (existing["id"],))

        self._store.execute(
            "UPDATE devices SET last_seen_at = ? WHERE id = ?",
            (now(), existing["id"]))

        # Re-read: `existing` predates the write.
        return self._store.one(
            "SELECT * FROM devices WHERE id = ?", (existing["id"],))

    def refresh(self, refresh_token: str, jkt: str,
                machine_id_hash: Optional[str] = None,
                machine_id_source: Optional[str] = None) -> dict:
        '''Rotate a session, always to the family's full scope.

        The proof's key is compared with the family's BEFORE reuse detection,
        so a refresh token held without the key ends nothing.
        '''
        import jwt

        try:
            claims = jwt.decode(refresh_token, self._secret,
                                algorithms=["HS256"],
                                options={"require": ["jti", "family", "exp"]})
        except jwt.PyJWTError:
            raise OAuthError("invalid_grant", "the refresh token does not verify") from None

        row = self._store.one(
            "SELECT rt.*, tf.user_id, tf.device_id, tf.scope, tf.dpop_jkt, "
            "       tf.revoked_at AS family_revoked_at, "
            "       tf.revoked_reason, tf.expires_at AS family_expires_at "
            "FROM refresh_tokens rt JOIN token_families tf ON tf.id = rt.family_id "
            "WHERE rt.jti = ?", (claims["jti"],))

        if row is None:
            raise OAuthError("invalid_grant", "unknown refresh token")

        # Before anything else: a stolen refresh token is useless without the key.
        if row["dpop_jkt"] != jkt:
            raise OAuthError("invalid_dpop_proof",
                             "this session is bound to a different key")

        if row["family_revoked_at"] is not None:
            raise self._grant_ended(_wire_reason(row["revoked_reason"]))

        timestamp = now()
        if row["replaced_at"] is not None:
            replaced = _seconds_since(row["replaced_at"], timestamp)
            if replaced > REFRESH_GRACE_SECONDS:
                # Reuse past the grace window with the family's key: leaked.
                self._revoke_family(row["family_id"], "reuse_detected")
                raise self._grant_ended("reused")
            # A retry of a lost response: the replacement, never a second one.
            replacement = self._store.one(
                "SELECT * FROM refresh_tokens WHERE jti = ?", (row["replaced_by"],))
            return self._tokens(row["user_id"], row["device_id"], row["dpop_jkt"],
                                row["scope"], row["family_id"],
                                replacement["jti"], replacement["issued_at"],
                                replacement["expires_at"], row["family_expires_at"])

        if timestamp >= row["family_expires_at"]:
            # Not revoked: the session cap passed, so the column stays NULL.
            raise self._grant_ended("expired")

        user = self._store.one("SELECT * FROM users WHERE id = ?", (row["user_id"],))
        if user["deactivated_at"] is not None:
            # Ends a deactivated account's sessions within one access lifetime.
            self._revoke_family(row["family_id"], "account_inactive")
            raise self._grant_ended("deactivated")

        self._check_fingerprint(row, machine_id_hash, machine_id_source)

        return self._rotate(row)

    def _check_fingerprint(self, row, machine_id_hash, machine_id_source) -> None:
        '''🔴 Step up, never revoke (identity §6): a refresh from a machine
        whose fingerprint changed is refused `invalid_grant` with no reason,
        and the session stays live. A device enrolled with `none` has no
        change detection.'''
        if not row["device_id"]:
            return
        device = self._store.one("SELECT machine_id_hash, machine_id_source FROM devices "
                                 "WHERE id = ?", (row["device_id"],))
        if device is None or device["machine_id_source"] == "none":
            return
        if (machine_id_source or "none", machine_id_hash or None) == \
                (device["machine_id_source"], device["machine_id_hash"]):
            return
        self._store.execute(
            "INSERT INTO device_events (device_id, kind) VALUES (?, 'machine_id_mismatch')",
            (row["device_id"],))
        raise OAuthError("invalid_grant",
                         "this machine's fingerprint is not the one this device "
                         "enrolled with; log in again")

    def _rotate(self, row) -> dict:
        timestamp = now()
        new_jti = str(uuid.uuid4())
        expires = _plus(timestamp, min(
            REFRESH_TOKEN_SECONDS,
            max(0, _seconds_since(timestamp, row["family_expires_at"]))))

        with self._store.transaction():
            self._store.execute(
                "INSERT INTO refresh_tokens (jti, family_id, issued_at, expires_at) "
                "VALUES (?, ?, ?, ?)", (new_jti, row["family_id"], timestamp, expires))
            self._store.execute(
                "UPDATE refresh_tokens SET replaced_by = ?, replaced_at = ? "
                "WHERE jti = ?", (new_jti, timestamp, row["jti"]))

            # 🔴 A rotation is the only use signal most devices give, since the
            # client refreshes rather than logs in again. Per rotation, not per
            # request, to spare a write on every call.
            if row["device_id"]:
                self._store.execute(
                    "UPDATE devices SET last_seen_at = ? WHERE id = ?",
                    (timestamp, row["device_id"]))

        return self._tokens(row["user_id"], row["device_id"], row["dpop_jkt"],
                            row["scope"], row["family_id"], new_jti, timestamp, expires,
                            row["family_expires_at"])

    def _issue(self, user_id: str, device_id: Optional[str], jkt: str,
               scope: str) -> dict:
        timestamp = now()
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        session_end = _plus(timestamp, SESSION_SECONDS)
        refresh_end = _plus(timestamp, REFRESH_TOKEN_SECONDS)

        self._store.execute(
            "INSERT INTO token_families "
            "(id, user_id, device_id, kind, dpop_jkt, scope, expires_at) "
            "VALUES (?, ?, ?, 'interactive', ?, ?, ?)",
            (family_id, user_id, device_id, jkt, scope, session_end))
        self._store.execute(
            "INSERT INTO refresh_tokens (jti, family_id, issued_at, expires_at) "
            "VALUES (?, ?, ?, ?)", (jti, family_id, timestamp, refresh_end))

        return self._tokens(user_id, device_id, jkt, scope, family_id,
                            jti, timestamp, refresh_end, session_end)

    def _tokens(self, user_id, device_id, jkt, scope, family_id,
                refresh_jti, refresh_issued, refresh_expires, session_expires) -> dict:
        import jwt

        issued = int(time.time())

        access = jwt.encode(
            {"iss": "sc-server", "sub": user_id, "iat": issued,
             "exp": issued + ACCESS_TOKEN_SECONDS, "jti": str(uuid.uuid4()),
             "scope": scope, "family": family_id, "device": device_id,
             # Usable only by whoever proves it holds the key.
             "cnf": {"jkt": jkt}},
            self._secret, algorithm="HS256")

        # From its row alone, so a grace-window retry gets the same token.
        refresh = jwt.encode(
            {"iss": "sc-server", "jti": refresh_jti, "family": family_id,
             "iat": int(parse(refresh_issued).timestamp()),
             "exp": int(parse(refresh_expires).timestamp())},
            self._secret, algorithm="HS256")

        return {
            "access_token": access,
            "token_type": "DPoP",
            "expires_in": ACCESS_TOKEN_SECONDS,
            "refresh_token": refresh,
            "refresh_token_expires_in": max(0, _seconds_between(refresh_expires)),
            "session_expires_in": max(0, _seconds_between(session_expires)),
            # REQUIRED on every grant, so absence never has two meanings.
            "scope": scope,
        }

    ######################################################################
    # Presenting
    ######################################################################

    def authenticate(self, authorization: Optional[str], proof: Optional[str],
                     method: str, url: str) -> Session:
        '''Verify an access token and the proof presented with it.'''
        if not authorization or not authorization.startswith("DPoP "):
            raise ProblemError(
                "invalid-token", detail="this endpoint needs a DPoP credential",
                headers={"WWW-Authenticate": "DPoP"})

        token = authorization[len("DPoP "):].strip()

        if not proof:
            raise ProblemError("invalid-dpop-proof", detail="no DPoP proof")

        try:
            jkt = dpop.verify_proof(proof, method, url, access_token=token)
        except dpop.DPoPError as e:
            raise ProblemError("invalid-dpop-proof", detail=str(e)) from None

        self._check_replay(proof)

        import jwt
        try:
            claims = jwt.decode(
                token, self._secret, algorithms=["HS256"],
                options={"require": ["sub", "exp", "scope", "family", "cnf"]})
        except jwt.ExpiredSignatureError:
            raise ProblemError(
                "invalid-token", detail="the access token has expired",
                headers={"WWW-Authenticate": 'DPoP error="invalid_token"'}) from None
        except jwt.PyJWTError:
            raise ProblemError(
                "invalid-token", detail="the access token does not verify",
                headers={"WWW-Authenticate": 'DPoP error="invalid_token"'}) from None

        if claims["cnf"].get("jkt") != jkt:
            raise ProblemError(
                "invalid-dpop-proof",
                detail="the proof key does not match the token")

        family = self._store.one(
            "SELECT * FROM token_families WHERE id = ?", (claims["family"],))
        if family is None or family["revoked_at"] is not None:
            # The client must re-authenticate, NOT refresh.
            reason = _wire_reason(family["revoked_reason"] if family else None)
            raise ProblemError("session-ended", reason=reason, detail=_ENDED.get(reason),
                               headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})

        # Best effort, with no security claim (profile §0): a token whose
        # family is another user's is not a token for this one.
        if family["user_id"] != claims["sub"]:
            raise ProblemError(
                "invalid-token", detail="the access token does not verify",
                headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})

        return Session(claims["sub"], claims["scope"], claims["family"],
                       claims.get("device"), jkt, expires_at=claims.get("exp"))

    def _check_replay(self, proof: str, oauth: bool = False) -> None:
        '''One proof, one request, remembered for the proof's lifetime.'''
        import jwt

        jti = jwt.decode(proof, options={"verify_signature": False}).get("jti")
        current = time.time()

        with self._seen_lock:
            for seen, when in list(self._seen.items()):
                if current - when > dpop.PROOF_LIFETIME_SECONDS * 2:
                    self._seen.pop(seen, None)
            replayed = jti in self._seen
            if not replayed:
                self._seen[jti] = current

        if replayed:
            if oauth:
                raise OAuthError("invalid_dpop_proof", "proof replayed")
            raise ProblemError("invalid-dpop-proof", detail="proof replayed")

    ######################################################################
    # Ending
    ######################################################################

    def revoke(self, session: Session) -> None:
        '''End this session.'''
        self._revoke_family(session.family_id, "user_logout")

    def _revoke_family(self, family_id: str, reason: str) -> None:
        self._store.execute(
            "UPDATE token_families SET revoked_at = ?, revoked_reason = ? "
            "WHERE id = ? AND revoked_at IS NULL",
            (now(), reason, family_id))

    def _retire_elsewhere(self, user_id: str, jkt: str) -> None:
        '''This key was last seen as somebody else. End that enrolment.

        🔴 A machine whose *derivation* changed and key did not (a reimage, a
        new uid): the old device row holds this UNIQUE thumbprint, and the
        insert would fail. Retired, not refused: the key's holder could already
        act as the previous user, and the event is recorded.
        '''
        stale = self._store.one(
            "SELECT * FROM devices WHERE dpop_jkt = ? AND revoked_at IS NULL "
            "AND user_id <> ?", (jkt, user_id))
        if stale is None:
            return

        logger.warning(
            f"device {stale['id']} presented a new identity: retiring its "
            f"enrolment as {stale['user_id']}")

        timestamp = now()
        self._store.execute(
            "UPDATE devices SET revoked_at = ? WHERE id = ?", (timestamp, stale["id"]))
        self._store.execute(
            "UPDATE token_families SET revoked_at = ?, "
            "revoked_reason = 'device_revoked' "
            "WHERE device_id = ? AND revoked_at IS NULL", (timestamp, stale["id"]))
        # actor_id stays NULL: nobody decided this, a derivation changed.
        self._store.execute(
            "INSERT INTO device_events (device_id, kind) VALUES (?, 'revoked')",
            (stale["id"],))

    def revoke_device(self, device_id: str, actor_id: str) -> None:
        '''Revoking a machine ends every session it holds.'''
        timestamp = now()
        with self._store.transaction():
            self._store.execute(
                "UPDATE devices SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (timestamp, device_id))
            self._store.execute(
                "UPDATE token_families SET revoked_at = ?, "
                "revoked_reason = 'device_revoked' "
                "WHERE device_id = ? AND revoked_at IS NULL",
                (timestamp, device_id))
            self._store.execute(
                "INSERT INTO device_events (device_id, kind, actor_id) "
                "VALUES (?, 'revoked', ?)", (device_id, actor_id))

    def release_binding(self, user_id: str, actor_id: str) -> int:
        '''The operator's release of a subject's key binding: its live device
        is revoked, so the next `client_credentials` call enrols whatever key
        it presents. Returns how many devices were released.'''
        devices = self._store.all(
            "SELECT id FROM devices WHERE user_id = ? AND revoked_at IS NULL", (user_id,))
        for device in devices:
            self.revoke_device(device["id"], actor_id)
        return len(devices)

    @staticmethod
    def _grant_ended(reason: str) -> OAuthError:
        '''The same condition at the token endpoint, in the OAuth shape.'''
        return OAuthError("invalid_grant", _ENDED.get(reason), reason=reason)


_ENDED = {"revoked": "this session was revoked",
          "reused": "this session was ended because its refresh token was used "
                    "twice: your credentials were used elsewhere",
          "deactivated": "this account is not active",
          "expired": "this session has aged out"}


def _wire_reason(stored: Optional[str]) -> str:
    """A stored revocation reason as the client's closed vocabulary; anything
    unrecognised is `revoked`."""
    return _WIRE_REASON.get(stored or "", "revoked")


def _load_or_create_secret(path: Path) -> bytes:
    '''The token signing secret, created on first start, 0600: whoever reads
    it can mint a session for any user.'''
    if path.exists():
        return path.read_bytes()

    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Created with the mode, never briefly readable by anyone else.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, secret)
    finally:
        os.close(fd)
    return secret


def _plus(timestamp: str, seconds: int) -> str:
    from datetime import timedelta

    return stamp(parse(timestamp) + timedelta(seconds=seconds))


def _seconds_since(earlier: str, later: str) -> float:
    return (parse(later) - parse(earlier)).total_seconds()


def _seconds_between(timestamp: str) -> int:
    return int(parse(timestamp).timestamp() - time.time())
