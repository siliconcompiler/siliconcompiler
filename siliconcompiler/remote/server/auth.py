'''
Sessions: minting them, presenting them, and ending them.

Nothing here verifies who a caller is -- this is the unauthenticated profile,
and the identity is self-asserted namespacing rather than a boundary. What it
does buy is the thing that was actually broken: a job has an owner, and a
stranger holding its id is not that owner.

The one real control is the key. On the first `client_credentials` issuance for
a subject the server records the presented thumbprint, and thereafter that
subject presenting a different key is refused. That closes the steady state:
once B has used the server, A cannot become B.
'''

import logging
import os
import secrets
import time

from pathlib import Path
from typing import Dict, Optional, Tuple

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import ProblemError
from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import Store, now

__all__ = [
    "SCOPES", "expand_scope", "TokenIssuer", "Session",
    "ACCESS_TOKEN_SECONDS", "REFRESH_TOKEN_SECONDS", "SESSION_SECONDS",
]


logger = logging.getLogger("sc-server")


# Six values, closed and frozen. Every one is <resource>:read or
# <resource>:write and there is no third shape, so a reader can tell what a
# value costs without consulting a table. The vocabulary being closed is what
# bounds a stolen token: it is these and nothing else, ever.
SCOPES = (
    "jobs:read",
    "jobs:write",
    "artifacts:read",
    "devices:read",
    "devices:write",
    "profile:read",
)

# Write carries read, and the expansion happens at mint rather than at check --
# so what is stored and what is published are the same string, and a client is
# never told it has less than it has.
_IMPLIES = {
    "jobs:write": "jobs:read",
    "devices:write": "devices:read",
}

ACCESS_TOKEN_SECONDS = 900          # 15 minutes
REFRESH_TOKEN_SECONDS = 604800      # 7 days, sliding
SESSION_SECONDS = 1036800           # 12 days, the family cap. NEVER extended

# A moment of overlap after a refresh token is replaced. Without it, a client
# whose response was lost retries with a token the server has already rotated
# and gets its whole session killed for reuse.
REFRESH_GRACE_SECONDS = 30

# Two vocabularies, deliberately different sizes, and this is the only place
# they meet. The column records WHY a family ended, in six values an operator
# reading the store wants; the wire carries WHAT THE CLIENT MUST DO, in three
# that are one branch each. Leaking the column's values would have a client
# branching on names the contract does not have.
_WIRE_REASON = {
    "user_logout": "revoked",
    "reuse_detected": "revoked",
    "device_revoked": "revoked",
    "ci_credential_revoked": "revoked",
    "admin": "revoked",
    "account_inactive": "deactivated",
}

_SIGNING_KEY_FILE = "token-signing-key"


def expand_scope(requested: Optional[str]) -> str:
    '''The scope a token is minted with.

    Omitting `scope` asks for everything this profile grants, which is all six:
    the caller is one self-asserted identity on a machine it already owns.
    '''
    if requested is None or not requested.strip():
        granted = set(SCOPES)
    else:
        asked = set(requested.split())
        unknown = asked - set(SCOPES)
        if unknown:
            raise ProblemError(
                "invalid-request",
                detail=f"unknown scope: {' '.join(sorted(unknown))}")
        granted = set(asked)

    for write, read in _IMPLIES.items():
        if write in granted:
            granted.add(read)

    # Published in the vocabulary's own order rather than sorted, so two tokens
    # with the same scope have the same string.
    return " ".join(scope for scope in SCOPES if scope in granted)


class _KeyMismatch(Exception):
    """A known subject presented a key that is not the one it is bound to."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(device_id)


class Session:
    '''A verified caller, for the duration of one request.'''

    def __init__(self, user_id: str, scope: str, family_id: str,
                 device_id: Optional[str], jkt: str):
        self.user_id = user_id
        self.scope = frozenset(scope.split())
        self.family_id = family_id
        self.device_id = device_id
        self.jkt = jkt

    def require(self, scope: str) -> None:
        '''Refuse unless the token covers this endpoint.

        The client fails rather than refreshing: a refresh re-mints the same
        ceiling, so retrying is a loop.
        '''
        if scope not in self.scope:
            raise ProblemError(
                "insufficient-scope",
                detail=f"this endpoint needs {scope}",
                headers={"WWW-Authenticate":
                         f'DPoP error="insufficient_scope", scope="{scope}"'})


class TokenIssuer:
    '''Mints and checks this deployment's tokens.

    Symmetric signing: one process both issues and verifies, and the token never
    leaves this deployment, so there is no second party needing a public half.
    '''

    def __init__(self, datadir: Path, store: Store, bind_keys: bool = True):
        self._store = store
        self._secret = _load_or_create_secret(Path(datadir) / _SIGNING_KEY_FILE)

        # Binding is ON by default, and turning it off declares the deployment a
        # single trust domain. A container fleet needs it off, because
        # /etc/machine-id is per image and every container derives the same
        # subject -- with binding on the first one binds and the rest are
        # refused. Off-by-default would fail silently, which is the wrong
        # direction: one user reads another's designs and nothing says so.
        self._bind_keys = bind_keys

        # Seen proof ids, so one cannot be replayed inside its window. Bounded
        # by the window rather than by a count: a proof older than that fails on
        # `iat` regardless.
        self._seen: Dict[str, float] = {}

    ######################################################################
    # Minting
    ######################################################################

    def client_credentials(self, subject: str, jkt: str,
                           requested_scope: Optional[str],
                           machine_id_hash: Optional[str] = None,
                           machine_id_source: str = "none",
                           display_name: Optional[str] = None) -> dict:
        '''Log in with no browser, no issuer and no human.

        The grant's shape is borrowed, not its guarantees: RFC 6749 assumes a
        confidential client with a real secret, and here the secret is nominal.
        Saying so is the honest version of what this profile is.
        '''
        try:
            with self._store.transaction():
                user = self._store.upsert_user(
                    "local", subject,
                    posix_account=subject,
                    display_name=display_name)

                if not user["is_active"]:
                    raise ProblemError(
                        "session-ended", reason="deactivated",
                        detail="this account is not active",
                        headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})

                device = self._bind_device(user["id"], jkt, machine_id_hash,
                                           machine_id_source, display_name)
                return self._issue(user["id"], device["id"], jkt,
                                   expand_scope(requested_scope))
        except _KeyMismatch as mismatch:
            # Recorded AFTER the transaction has rolled back, and deliberately.
            # device_events is append-only and is the half of this story with a
            # reader: somebody presenting the wrong key for a known subject is
            # the one event in this profile worth keeping, and writing it inside
            # the transaction the refusal aborts would throw it away.
            self._store.execute(
                "INSERT INTO device_events (device_id, kind) "
                "VALUES (?, 'reauth_failed')", (mismatch.device_id,))
            logger.warning(
                f"refused a session for a known subject presenting a different "
                f"key (device {mismatch.device_id})")
            raise ProblemError(
                "invalid-dpop-proof",
                detail="this subject is bound to a different key",
                headers={"WWW-Authenticate": 'DPoP error="invalid_client"'}) from None

    def _bind_device(self, user_id: str, jkt: str,
                     machine_id_hash: Optional[str],
                     machine_id_source: str,
                     display_name: Optional[str]):
        '''First contact records the key; later contact must present it.

        Without this, A on a shared machine presents B's derivation with A's own
        key and gets a session as B -- and the derivation is public knowledge,
        so the claim costs nothing to forge.
        '''
        existing = self._store.one(
            "SELECT * FROM devices WHERE user_id = ? AND revoked_at IS NULL",
            (user_id,))

        if existing is None:
            device_id = str(uuid7())
            self._store.execute(
                "INSERT INTO devices "
                "(id, user_id, name, dpop_jkt, machine_id_hash, machine_id_source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (device_id, user_id, display_name or "this machine", jkt,
                 machine_id_hash, machine_id_source))
            self._store.execute(
                "INSERT INTO device_events (device_id, kind) VALUES (?, 'enrolled')",
                (device_id,))
            return self._store.one("SELECT * FROM devices WHERE id = ?", (device_id,))

        if existing["dpop_jkt"] != jkt:
            if self._bind_keys:
                # Raised rather than answered here, so that the caller can
                # record the attempt once this transaction has rolled back.
                raise _KeyMismatch(existing["id"])

            # Binding off: the deployment has declared itself one trust domain,
            # so the newest key wins and the change is recorded rather than
            # refused.
            self._store.execute(
                "UPDATE devices SET dpop_jkt = ?, last_seen_at = ? WHERE id = ?",
                (jkt, now(), existing["id"]))
            return self._store.one(
                "SELECT * FROM devices WHERE id = ?", (existing["id"],))

        self._store.execute(
            "UPDATE devices SET last_seen_at = ? WHERE id = ?",
            (now(), existing["id"]))
        return existing

    def refresh(self, refresh_token: str, jkt: str,
                requested_scope: Optional[str]) -> dict:
        '''Rotate a session, without widening it.'''
        import jwt

        try:
            claims = jwt.decode(refresh_token, self._secret,
                                algorithms=["HS256"],
                                options={"require": ["jti", "family", "exp"]})
        except jwt.PyJWTError:
            raise ProblemError(
                "invalid-token", detail="the refresh token does not verify",
                headers={"WWW-Authenticate": 'DPoP error="invalid_token"'}) from None

        row = self._store.one(
            "SELECT rt.*, tf.user_id, tf.device_id, tf.scope, tf.dpop_jkt, "
            "       tf.revoked_at AS family_revoked_at, "
            "       tf.revoked_reason, tf.absolute_expires_at "
            "FROM refresh_tokens rt JOIN token_families tf ON tf.id = rt.family_id "
            "WHERE rt.jti = ?", (claims["jti"],))

        if row is None:
            raise ProblemError(
                "invalid-token", detail="unknown refresh token",
                headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})

        if row["family_revoked_at"] is not None:
            raise self._session_ended(_wire_reason(row["revoked_reason"]))

        # The key the family is bound to, checked on every refresh. This is
        # where a stolen refresh token stops being useful to anything that does
        # not also hold the key.
        if row["dpop_jkt"] != jkt:
            raise ProblemError(
                "invalid-dpop-proof",
                detail="this session is bound to a different key")

        timestamp = now()
        if row["replaced_at"] is not None:
            replaced = _seconds_since(row["replaced_at"], timestamp)
            if replaced > REFRESH_GRACE_SECONDS:
                # Reuse past the grace window is the signal the whole family has
                # leaked, so the session ends rather than the request failing.
                self._revoke_family(row["family_id"], "reuse_detected")
                raise self._session_ended("revoked")
            # Inside the window: a retry of a lost response, not an attack.
            return self._replay_refresh(row)

        if timestamp >= row["absolute_expires_at"]:
            # Not revoked: nothing decided this, the session cap simply passed.
            # The column stays NULL and the client is told to log in again.
            raise self._session_ended("expired")

        user = self._store.one("SELECT * FROM users WHERE id = ?", (row["user_id"],))
        if not user["is_active"]:
            # Re-read on every refresh, so deactivating an account ends its
            # sessions within one access-token lifetime.
            self._revoke_family(row["family_id"], "account_inactive")
            raise self._session_ended("deactivated")

        # A rotation may narrow inside the family's ceiling, never widen past
        # it. Omitting `scope` returns to the ceiling.
        ceiling = set(row["scope"].split())
        granted = ceiling if requested_scope is None else \
            set(expand_scope(requested_scope).split()) & ceiling

        return self._rotate(row, " ".join(s for s in SCOPES if s in granted))

    def _replay_refresh(self, row) -> dict:
        replacement = self._store.one(
            "SELECT * FROM refresh_tokens WHERE jti = ?", (row["replaced_by"],))
        return self._tokens(row["user_id"], row["device_id"], row["dpop_jkt"],
                            row["scope"], row["family_id"],
                            replacement["jti"], replacement["expires_at"],
                            row["absolute_expires_at"])

    def _rotate(self, row, scope: str) -> dict:
        timestamp = now()
        new_jti = str(uuid7())
        expires = _plus(timestamp, min(
            REFRESH_TOKEN_SECONDS,
            max(0, _seconds_since(timestamp, row["absolute_expires_at"]))))

        with self._store.transaction():
            self._store.execute(
                "INSERT INTO refresh_tokens (jti, family_id, expires_at) "
                "VALUES (?, ?, ?)", (new_jti, row["family_id"], expires))
            self._store.execute(
                "UPDATE refresh_tokens SET replaced_by = ?, replaced_at = ? "
                "WHERE jti = ?", (new_jti, timestamp, row["jti"]))
            if scope != row["scope"]:
                self._store.execute(
                    "UPDATE token_families SET scope = ? WHERE id = ?",
                    (scope, row["family_id"]))

        return self._tokens(row["user_id"], row["device_id"], row["dpop_jkt"],
                            scope, row["family_id"], new_jti, expires,
                            row["absolute_expires_at"])

    def _issue(self, user_id: str, device_id: Optional[str], jkt: str,
               scope: str) -> dict:
        timestamp = now()
        family_id = str(uuid7())
        jti = str(uuid7())

        session_end = _plus(timestamp, SESSION_SECONDS)
        refresh_end = _plus(timestamp, REFRESH_TOKEN_SECONDS)

        self._store.execute(
            "INSERT INTO token_families "
            "(id, user_id, device_id, kind, dpop_jkt, scope, absolute_expires_at) "
            "VALUES (?, ?, ?, 'interactive', ?, ?, ?)",
            (family_id, user_id, device_id, jkt, scope, session_end))
        self._store.execute(
            "INSERT INTO refresh_tokens (jti, family_id, expires_at) VALUES (?, ?, ?)",
            (jti, family_id, refresh_end))

        return self._tokens(user_id, device_id, jkt, scope, family_id,
                            jti, refresh_end, session_end)

    def _tokens(self, user_id, device_id, jkt, scope, family_id,
                refresh_jti, refresh_expires, session_expires) -> dict:
        import jwt

        issued = int(time.time())

        access = jwt.encode(
            {"iss": "sc-server", "sub": user_id, "iat": issued,
             "exp": issued + ACCESS_TOKEN_SECONDS, "jti": str(uuid7()),
             "scope": scope, "family": family_id, "device": device_id,
             # The confirmation claim: this token is only usable by something
             # that can prove it holds the key.
             "cnf": {"jkt": jkt}},
            self._secret, algorithm="HS256")

        refresh = jwt.encode(
            {"iss": "sc-server", "jti": refresh_jti, "family": family_id,
             "iat": issued,
             "exp": issued + max(0, _seconds_between(refresh_expires))},
            self._secret, algorithm="HS256")

        return {
            "access_token": access,
            # Never "Bearer": a bearer token is exactly the shape this exists to
            # avoid.
            "token_type": "DPoP",
            "expires_in": ACCESS_TOKEN_SECONDS,
            "refresh_token": refresh,
            "refresh_token_expires_in": max(0, _seconds_between(refresh_expires)),
            "session_expires_in": max(0, _seconds_between(session_expires)),
            # REQUIRED on every grant, and not merely when it differs from what
            # was asked: absent would mean "you got what you asked for" on one
            # server and "we do not publish this" on another.
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
            raise self._session_ended(
                _wire_reason(family["revoked_reason"] if family else None))

        return Session(claims["sub"], claims["scope"], claims["family"],
                       claims.get("device"), jkt)

    def _check_replay(self, proof: str) -> None:
        '''One proof, one request.

        The window is the proof's own lifetime: anything older fails on `iat`
        before it reaches here, so nothing has to be remembered past that.
        '''
        import jwt

        jti = jwt.decode(proof, options={"verify_signature": False}).get("jti")
        current = time.time()

        for seen, when in list(self._seen.items()):
            if current - when > dpop.PROOF_LIFETIME_SECONDS * 2:
                self._seen.pop(seen, None)

        if jti in self._seen:
            raise ProblemError("invalid-dpop-proof", detail="proof replayed")
        self._seen[jti] = current

    ######################################################################
    # Ending
    ######################################################################

    def revoke(self, session: Session) -> None:
        '''End this session. No scope gates it: a logout that can be scoped
        away is a session nobody can close.'''
        self._revoke_family(session.family_id, "user_logout")

    def _revoke_family(self, family_id: str, reason: str) -> None:
        self._store.execute(
            "UPDATE token_families SET revoked_at = ?, revoked_reason = ? "
            "WHERE id = ? AND revoked_at IS NULL",
            (now(), reason, family_id))

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

    @staticmethod
    def _session_ended(reason: str) -> ProblemError:
        '''The client must re-authenticate and must NOT refresh.

        All three reasons are one client branch, which is why they are one slug
        with a `reason` member rather than three slugs.
        '''
        return ProblemError(
            "session-ended", reason=reason,
            detail={"revoked": "this session was revoked",
                    "deactivated": "this account is not active",
                    "expired": "this session has aged out"}.get(reason),
            headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})


def _wire_reason(stored: Optional[str]) -> str:
    """Translate a stored revocation reason into the one the client branches on.

    An unrecognised value maps to `revoked` rather than passing through: the
    wire vocabulary is closed, and a client that meets a fourth value has no
    branch for it.
    """
    return _WIRE_REASON.get(stored or "", "revoked")


def _load_or_create_secret(path: Path) -> bytes:
    '''The token signing secret, created on first start.

    0600 and no wider: anything that can read it can mint a session for any
    user on this deployment.
    '''
    if path.exists():
        return path.read_bytes()

    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Opened with the mode rather than chmod'ed afterwards, so the file is never
    # briefly readable by anyone else.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, secret)
    finally:
        os.close(fd)
    return secret


def _plus(timestamp: str, seconds: int) -> str:
    from datetime import datetime, timedelta, timezone

    moment = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse(timestamp: str) -> float:
    from datetime import datetime, timezone

    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=timezone.utc).timestamp()


def _seconds_since(earlier: str, later: str) -> float:
    return _parse(later) - _parse(earlier)


def _seconds_between(timestamp: str) -> int:
    return int(_parse(timestamp) - time.time())


def scope_for(session: Optional[Session]) -> Tuple[str, ...]:
    return tuple(sorted(session.scope)) if session else ()
