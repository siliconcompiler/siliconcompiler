'''
Sessions: minting, presenting and ending them.

Identity here is self-asserted namespacing: it buys ownership, not a boundary.
The one control is the key. The first `client_credentials` login for a subject
binds its DPoP key to a device, and a different key is refused until that
device is revoked.
'''

import hashlib
import secrets
import threading
import time
import uuid

from typing import Optional

import jwt

from siliconcompiler.remote import dpop
from siliconcompiler.remote.server.errors import OAuthError, ProblemError
from siliconcompiler.remote.server.state.store import Store

__all__ = ["Identity", "Session"]


ACCESS_SECONDS = 900
REFRESH_SECONDS = 7 * 86400
# The cap on a session, however often it refreshes.
SESSION_SECONDS = 12 * 86400


class Session:
    '''A verified caller, for one request.'''

    def __init__(self, row):
        self.user_id = row["user_id"]
        self.device_id = row["device_id"]
        self.session_id = row["session_id"]
        self.access_expires_at = row["expires_at"]
        self.session_expires_at = row["session_expires_at"]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _invalid_token(detail: str) -> ProblemError:
    return ProblemError("invalid-token", detail=detail,
                        headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})


class Identity:
    def __init__(self, store: Store):
        self._store = store
        # Proof ids seen inside the proof window; an older proof fails on `iat`.
        self._seen = {}
        self._seen_lock = threading.Lock()

    def check_proof(self, proof: Optional[str], method: str, urls, access_token=None) -> str:
        '''The key a proof is signed with, if it is good for one of ``urls``
        (the request's own, or each origin the server is configured to be
        reached at) and has not been used before. DPoPError otherwise.'''
        if not proof:
            raise dpop.DPoPError("a DPoP proof is required")

        for url in urls:
            try:
                jkt = dpop.verify_proof(proof, method, url, access_token=access_token)
                break
            except dpop.DPoPError as e:
                refusal = e
        else:
            raise refusal

        jti = jwt.decode(proof, options={"verify_signature": False})["jti"]
        current = time.time()
        with self._seen_lock:
            for seen, when in list(self._seen.items()):
                if current - when > dpop.PROOF_LIFETIME_SECONDS * 2:
                    del self._seen[seen]
            if jti in self._seen:
                raise dpop.DPoPError("proof replayed")
            self._seen[jti] = current
        return jkt

    def client_credentials(self, subject: str, jkt: str, name: Optional[str],
                           machine_id_source: str) -> dict:
        timestamp = time.time()
        with self._store.transaction():
            self._store.execute(
                "INSERT OR IGNORE INTO users (id, issuer, subject, display_name, created_at) "
                "VALUES (?, 'local', ?, ?, ?)", (str(uuid.uuid4()), subject, name, timestamp))
            user = self._store.one(
                "SELECT id FROM users WHERE issuer = 'local' AND subject = ?", (subject,))

            device = self._store.one(
                "SELECT id, jkt FROM devices WHERE user_id = ? AND revoked_at IS NULL",
                (user["id"],))
            if device is None:
                device = {"id": str(uuid.uuid4()), "jkt": jkt}
                self._store.execute(
                    "INSERT INTO devices (id, user_id, name, jkt, machine_id_source, "
                    "enrolled_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (device["id"], user["id"], name or "this machine", jkt,
                     machine_id_source, timestamp, timestamp))
            elif device["jkt"] != jkt:
                raise OAuthError(
                    "invalid_client", "this subject is bound to a different key; "
                    "retrying will not help", status=401)
            else:
                self._store.execute("UPDATE devices SET last_seen_at = ? WHERE id = ?",
                                    (timestamp, device["id"]))

            return self._issue(user["id"], device["id"], jkt, str(uuid.uuid4()),
                               timestamp + SESSION_SECONDS)

    def refresh(self, refresh_token: str, jkt: str) -> dict:
        '''Rotate: the token presented is spent, and only its replacement works.'''
        timestamp = time.time()
        with self._store.transaction():
            row = self._store.one("SELECT * FROM tokens WHERE hash = ? AND kind = 'refresh'",
                                  (_hash(refresh_token),))
            if row is None or row["expires_at"] <= timestamp:
                raise OAuthError("invalid_grant", "the refresh token is not valid")
            # Before the session's own state: a token held without its key proves nothing.
            if row["jkt"] != jkt:
                raise OAuthError("invalid_dpop_proof", "this session is bound to a different key")
            if row["revoked_at"] is not None:
                raise OAuthError("invalid_grant", "this session was revoked", reason="revoked")

            self._store.execute("DELETE FROM tokens WHERE hash = ?", (row["hash"],))
            self._store.execute("UPDATE devices SET last_seen_at = ? WHERE id = ?",
                                (timestamp, row["device_id"]))
            return self._issue(row["user_id"], row["device_id"], jkt, row["session_id"],
                               row["session_expires_at"])

    def _issue(self, user_id, device_id, jkt, session_id, session_end) -> dict:
        from siliconcompiler.remote.server.config import SCOPES

        timestamp = time.time()
        refresh_end = min(timestamp + REFRESH_SECONDS, session_end)
        # Dead rows would only pile up; a day past expiry, nothing looks for them.
        self._store.execute("DELETE FROM tokens WHERE expires_at < ?", (timestamp - 86400,))

        tokens = {}
        for kind, expires in (("access", timestamp + ACCESS_SECONDS),
                              ("refresh", refresh_end)):
            tokens[kind] = secrets.token_urlsafe(32)
            self._store.execute(
                "INSERT INTO tokens (hash, kind, session_id, user_id, device_id, jkt, "
                "expires_at, session_expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_hash(tokens[kind]), kind, session_id, user_id, device_id, jkt,
                 expires, session_end))

        return {
            "access_token": tokens["access"],
            "token_type": "DPoP",
            "expires_in": ACCESS_SECONDS,
            "refresh_token": tokens["refresh"],
            "refresh_token_expires_in": int(refresh_end - timestamp),
            "session_expires_in": int(session_end - timestamp),
            "scope": " ".join(SCOPES),
        }

    def authenticate(self, authorization: Optional[str], proof: Optional[str],
                     method: str, urls) -> Session:
        '''Verify an access token and the proof presented with it.'''
        if not authorization or not authorization.startswith("DPoP "):
            raise ProblemError("invalid-token", detail="this endpoint needs a DPoP credential",
                               headers={"WWW-Authenticate": "DPoP"})
        token = authorization[len("DPoP "):].strip()

        try:
            jkt = self.check_proof(proof, method, urls, access_token=token)
        except (dpop.DPoPError, UnicodeEncodeError) as e:
            raise ProblemError(
                "invalid-dpop-proof", detail=str(e),
                headers={"WWW-Authenticate": 'DPoP error="invalid_dpop_proof"'}) from None

        row = self._store.one("SELECT * FROM tokens WHERE hash = ? AND kind = 'access'",
                              (_hash(token),))
        if row is None or row["expires_at"] <= time.time():
            raise _invalid_token("the access token is not valid")
        if row["jkt"] != jkt:
            raise ProblemError(
                "invalid-dpop-proof", detail="the proof key does not match the token",
                headers={"WWW-Authenticate": 'DPoP error="invalid_dpop_proof"'})
        if row["revoked_at"] is not None:
            # The client logs in afresh, where an expired token only refreshes.
            raise ProblemError("session-ended", reason="revoked",
                               detail="this session was revoked",
                               headers={"WWW-Authenticate": 'DPoP error="invalid_token"'})
        return Session(row)

    def revoke_session(self, session_id: str) -> None:
        self._store.execute("UPDATE tokens SET revoked_at = ? WHERE session_id = ? "
                            "AND revoked_at IS NULL", (time.time(), session_id))

    def revoke_device(self, device_id: str) -> None:
        '''End every session a machine holds, and free its subject for another key.'''
        timestamp = time.time()
        with self._store.transaction():
            self._store.execute("UPDATE devices SET revoked_at = ? WHERE id = ? "
                                "AND revoked_at IS NULL", (timestamp, device_id))
            self._store.execute("UPDATE tokens SET revoked_at = ? WHERE device_id = ? "
                                "AND revoked_at IS NULL", (timestamp, device_id))
